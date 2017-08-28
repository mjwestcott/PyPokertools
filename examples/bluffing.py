"""
What properties does my hand have on the flop?

Poker analysis libraries commonly classify five-card poker hands according to a
scheme which allows two hands to be compared at showdown; they can find whether
my hand is a pair, straight, or flush etc., and rank them accordingly. This is
useful on the river when hand strengths are final.

However, on the flop things are different. First, there are many more
properties that may be of interest: whether we have a draw (and whether it's a
draw to the nuts), whether we have two overcards, etc. Second, some properties,
such as having 'three-to-a-straight' dont require all five cards, in which case
we want to know whether the property is the result of using _both_ our
holecards.

In this module you will find functions to find hands which satisfy these three
properties:
    - they have three-to-a-flush using both hole cards,
    - they have three-to-a-straight using both hole cards, and
    - they do not have a pair or better.
Expert poker players will recognise these as good candidates to use as bluffs.
"""
from collections import Counter
from functools import wraps
from itertools import chain

from pokertools import (
    CANONICAL_HOLECARDS,
    sorted_count_of_values,
    sorted_numerical_ranks,
    num_suits,
)
from properties.hand import is_nopair


#------------------------------------------------------------------------------
# Complex Hand Propeties
#
# In this section it is important to keep track of our holecards. As a
# result, these functions accept two positional arguments:
#     - holecards, a list of two cards
#     - flop, a list of three cards
# We can use this decorator to ensure that these arguments, when flattened
# by itertools.chain, comprise exactly five non-conflicting cards.


class ConflictingCards(Exception):
    pass


def five_cards(f):
    """
    A decorator to check that a function is passed exactly five cards
    in its positional arguments.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        cards = list(chain(*args))
        n = len(cards)
        if n != 5:
            raise ValueError("Exactly five cards must be passed to {}".format(f.__name__))
        if n != len(set(cards)):
            raise ConflictingCards("Conflicting cards passed to {}: {}".format(f.__name__, cards))
        return f(*args, **kwargs)
    return wrapper


@five_cards
def is_3straight(holecards, flop, required_holecards=2):
    """
    Returns a bool indicating whether our holecards have three-to-a-straight
    on this flop. Three-to-a-straight means that there exists a combination of
    three of the five total cards that is consecutive in rank.

    (Specify how many of our holecards must be part of the combination using
    required_holecards.  Default is 2 since this is intended to represent a
    property of those holecards that make it a good candidate for bluffing. A
    value 1 means at least 1.)

    Args:
        holecards (list): two pokertools.Card objects
        flop (list): three pokertools.Card objects

    Kwargs:
        required_holecards (int): from 0-2 specifying how many of our
            holecards are required to satisfy the property.

    Returns:
        True if the hand has the property three-to-a-straight on this flop
            with the required number of holecards;
        False otherwise

    Examples:
        >>> from pokertools import CARDS, HOLECARDS
        >>> my_holecards = HOLECARDS['4d 5c']
        >>> flop = [CARDS['Qd'], CARDS['3h'], CARDS['Kh']]
        >>> is_3straight(my_holecards, flop)
        True

        >>> my_holecards = HOLECARDS['2h 3c']
        >>> flop = [CARDS['8h'], CARDS['7h'], CARDS['6h']]
        >>> is_3straight(my_holecards, flop)
        False
    """
    assert 0 <= required_holecards <= 2

    rank1, rank2 = sorted_numerical_ranks(holecards)
    hand = list(chain(holecards, flop))
    ranks = sorted_numerical_ranks(hand)

    def subseqs():
        for i in range(len(ranks) - 2):
            yield ranks[i:i + 3]
        a, b, _, _, c = ranks  # Special case for Ace playing low
        if [a, b, c] == [2, 3, 14]:
            yield [a, b, c]

    for subseq in subseqs():
        x, y, z = subseq
        if x == y-1 == z-2 or [x, y, z] == [2, 3, 14]:
            if required_holecards == 2:
                if rank1 in subseq and rank2 in subseq:
                    return True
            elif required_holecards == 1:
                if rank1 in subseq or rank2 in subseq:
                    return True
            elif required_holecards == 0:
                return True
    return False


@five_cards
def is_3flush(holecards, flop, required_holecards=2):
    """
    Returns a bool indicating whether our holecards have three-to-a-flush
    on this flop. Three-to-a-flush means that there exists a combination of
    three of the five total cards which have the same suit.

    (Specify how many of our holecards must be part of the combination using
    required_holecards. Default is 2 since this is intended to represent a
    property of those holecards that make it a good candidate for bluffing. A
    value 1 means at least 1.)

    Args:
        holecards (list): two pokertools.Card objects
        flop (list): three pokertools.Card objects

    Kwargs:
        required_holecards (int): from 0-2 specifying how many of our
            holecards are required to satisfy the property

    Returns:
        True if holecards has the property three-to-a-flush on this flop;
        False otherwise

    Examples:
        >>> from pokertools import CARDS, HOLECARDS
        >>> my_holecards = HOLECARDS['2d 3d']
        >>> flop = [CARDS['7d'], CARDS['Qh'], CARDS['Kh']]
        >>> is_3flush(my_holecards, flop)
        True

        >>> my_holecards = HOLECARDS['2h 3d']
        >>> flop = [CARDS['7h'], CARDS['Ah'], CARDS['Kd']]
        >>> is_3flush(my_holecards, flop)
        False
    """
    assert 0 <= required_holecards <= 2

    suit1, suit2 = [card.suit for card in holecards]
    hand = list(chain(holecards, flop))
    suit_counts = Counter([card.suit for card in hand])

    for suit in suit_counts:
        if suit_counts[suit] == 3:
            if required_holecards == 2 and (suit1 == suit2 == suit):
                return True
            elif required_holecards == 1:
                if (suit1 == suit or suit2 == suit):
                    return True
            elif required_holecards == 0:
                return True
    return False

#------------------------------------------------------------------------------
# Bluff Candidates


@five_cards
def is_bluffcandidate(holecards, flop):
    """
    Returns a bool indicating whether our holecards are a good
    candidate for bluffing.

    Checks whether our hand has three properties:
        - three-to-a-flush using both hole cards       (see is_3flush())
        - three-to-a-straight using both hole cards    (see is_3straight())
        - not(pair-or-better)                          (see is_nopair())

    Args:
        holecards (list): two pokertools.Card objects
        flop (list): three pokertools.Card objects

    Returns:
        True if holecards has the properties listed above on this flop;
        False otherwise

    Example:
        >>> from pokertools import CARDS, HOLECARDS
        >>> my_holecards = HOLECARDS['2d 3d']
        >>> flop = [CARDS['7d'], CARDS['As'], CARDS['Kh']]
        >>> is_bluffcandidate(my_holecards, flop)
        True

        >>> my_holecards = HOLECARDS['2h 3c']
        >>> flop = [CARDS['8h'], CARDS['7h'], CARDS['6h']]
        >>> is_bluffcandidate(my_holecards, flop)
        False
    """
    hand = list(chain(holecards, flop))
    return (
        is_nopair(hand)
        and is_3flush(holecards, flop, required_holecards=2)
        and is_3straight(holecards, flop, required_holecards=2)
    )


def get_bluffcandidates(flop):
    for holecards in CANONICAL_HOLECARDS.values():
        try:
            if is_bluffcandidate(holecards, flop):
                yield holecards
        except ConflictingCards:
            pass
