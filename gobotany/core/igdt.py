'''An implementation of Information Gain and Decision Tree compilation.
Much of the implementation was pulled from the (assumed) public domain
code located at:
  http://onlamp.com/python/2006/02/09/examples/dtree.tar.gz
  http://onlamp.com/pub/a/python/2006/02/09/ai_decision_trees.html?page=1
'''
import math
from collections import defaultdict

from gobotany.core.models import CharacterValue, TaxonCharacterValue

def get_best_characters(pile, species_list):
    """Find the most effective characters for narrowing down these species.

    The return value will be an already-sorted list of tuples, each of
    which looks like::

        (entropy, character_id)

    """
    n = float(len(species_list))

    # Select all of the character values for these species.  We go ahead
    # and turn this into a list because we will iterate across it twice.

    taxon_character_values = list(
        TaxonCharacterValue.objects.filter(taxon__in=species_list)
        )

    # Count how many times each character value occurs amongst this
    # particular set of species.

    cv_species_counts = defaultdict(int)
    for tcv in taxon_character_values:
        cv_species_counts[tcv.character_value_id] += 1

    # Remove character values from the dictionary that do not belong to
    # the pile under consideration.

    pile_cv_ids = set( cv.id for cv in pile.character_values.all() )

    for cv_id in list(cv_species_counts):
        if cv_id not in pile_cv_ids:
            del cv_species_counts[cv_id]

    # Loop over the actual character-value objects whose IDs we just
    # listed, and update a `cvalues` dictionary whose keys are character
    # IDs and whose values are sets of character values - the character
    # values belonging to that character.  Also create a mapping from
    # character-value ID to character ID, to help us with our next loop.

    cvalues = defaultdict(set)
    id_to_character_value = {}

    for cv in CharacterValue.objects.filter(id__in=list(cv_species_counts)):
        cvalues[cv.character_id].add(cv)
        id_to_character_value[cv.id] = cv

    # Create a dictionary `cspecies` of character IDs keys whose values
    # are the set of species that have some character value that belongs
    # to the given character.  This lets us detect which characters
    # apply to only a small fraction of species, and which provide
    # nearly every species with at least one character value.

    cspecies = defaultdict(set)

    for tcv in taxon_character_values:
        cv = id_to_character_value.get(tcv.character_value_id, None)
        if cv is not None:  # since this might be an out-of-Pile char. value
            cspecies[cv.character_id].add(tcv.taxon_id)

    # For each character (which, for efficiency, we know only by its ID
    # at this point), compute the entropy that will remain if we split
    # this group of species by that character's values.  We save this as
    # a list of (entropy, character_id) tuples.  Note that we penalize
    # characters which only apply to a small fraction of the species we
    # are looking at.

    def f_entropy(m, n):
        return m / n * math.log(m, 2.)

    entropies = []
    for character_id, character_values in cvalues.iteritems():
        entropy = sum( f_entropy(cv_species_counts[character_value.id], n)
                       for character_value in character_values )
        coverage = len(cspecies[character_id]) / n
        penalty = 1. / coverage  # since small entropy is better
        entropies.append((entropy * penalty, character_id))

    # Sort the resulting list and return it.

    entropies.sort()
    return entropies


# From here down is old code to refactor and incorporate when appropriate.

class InformationTheoretic(object):

    def entropy(self, data, target_attr):
        """
        Calculates the entropy of the given data set for the target attribute.
        """
        val_freq = {}
        data_entropy = 0.0

        # Calculate the frequency of each of the values in the target attr
        for record in data:
            if record[target_attr] in val_freq:
                val_freq[record[target_attr]] += 1.0
            else:
                val_freq[record[target_attr]] = 1.0

        # Calculate the entropy of the data for the target attribute
        for freq in val_freq.values():
            data_entropy += (-freq / len(data)) * math.log(freq / len(data), 2)

        return data_entropy

    def gain(self, data, attr, target_attr):
        """
        Calculates the information gain (reduction in entropy) that would
        result by splitting the data on the chosen attribute (attr).
        """
        val_freq = {}
        subset_entropy = 0.0

        # Calculate the frequency of each of the values in the target attribute
        for record in data:
            if record[attr] in val_freq:
                val_freq[record[attr]] += 1.0
            else:
                val_freq[record[attr]] = 1.0

        # Calculate the sum of the entropy for each subset of records weighted
        # by their probability of occuring in the training set.
        for val in val_freq.keys():
            val_prob = val_freq[val] / sum(val_freq.values())
            data_subset = [record for record in data if record[attr] == val]
            subset_entropy += val_prob * self.entropy(data_subset, target_attr)

        # Subtract the entropy of the chosen attribute from the entropy of the
        # whole data set with respect to the target attribute (and return it)
        return (self.entropy(data, target_attr) - subset_entropy)


class DecisionTree(object):
    '''Decision tree maker.

    >>> lines = """
    ... Age, Education, Income, Marital Status, Purchase?
    ... 36 - 55, masters, high, single, will buy
    ... 18 - 35, high school, low, single, won't buy
    ... 36 - 55, masters, low, single, will buy
    ... 18 - 35, bachelors, high, single, won't buy
    ... < 18, high school, low, single, will buy
    ... 18 - 35, bachelors, high, married, won't buy
    ... 36 - 55, bachelors, low, married, won't buy
    ... > 55, bachelors, high, single, will buy
    ... 36 - 55, masters, low, married, won't buy
    ... > 55, masters, low, married, will buy
    ... 36 - 55, masters, high, single, will buy
    ... > 55, masters, high, single, will buy
    ... < 18, high school, high, single, won't buy
    ... 36 - 55, masters, low, single, will buy
    ... 36 - 55, high school, low, single, will buy
    ... < 18, high school, low, married, will buy
    ... 18 - 35, bachelors, high, married, won't buy
    ... > 55, high school, high, married, will buy
    ... > 55, bachelors, low, single, will buy
    ... 36 - 55, high school, high, married, won't buy
    ... """

    >>> lines = [x.strip() for x in lines.split('\\n') if x.strip()]
    >>> lines.reverse()
    >>> attributes = [attr.strip() for attr in lines.pop().split(",")]
    >>> target_attr = attributes[-1]
    >>> lines.reverse()

    >>> data = []
    >>> for line in lines:
    ...     data.append(dict(zip(attributes,
    ...     [datum.strip() for datum in line.split(",")])))

    >>> examples = data[:]
    >>> dt = DecisionTree(data, attributes, target_attr)
    >>> for item in dt.classify(examples):
    ...    print item
    will buy
    won't buy
    will buy
    won't buy
    will buy
    won't buy
    won't buy
    will buy
    won't buy
    will buy
    will buy
    will buy
    won't buy
    will buy
    will buy
    will buy
    won't buy
    will buy
    will buy
    won't buy

    '''

    def __init__(self, data, attribs, target_attr):
        self._ig = InformationTheoretic()
        self._treedata = self._create_decision_tree(data, attribs, target_attr)

    def classify(self, data):
        """
        Returns a list of classifications for each of the records in the data
        list as determined by the given decision tree.
        """
        return (self._get_classification(record)
                for record in data)

    def _majority_value(self, data, target_attr):
        """
        Creates a list of all values in the target attribute for each record
        in the data list object, and returns the value that appears in this
        list the most frequently.
        """
        data = data[:]
        return self._most_frequent([record[target_attr] for record in data])

    def _most_frequent(self, lst):
        """
        Returns the item that appears most frequently in the given list.
        """
        lst = lst[:]
        highest_freq = 0
        most_freq = None

        for val in self._unique(lst):
            if lst.count(val) > highest_freq:
                most_freq = val
                highest_freq = lst.count(val)

        return most_freq

    def _unique(self, lst):
        """
        Returns a list made up of the unique values found in lst.  i.e., it
        removes the redundant values in lst.
        """
        lst = lst[:]
        unique_lst = []

        # Cycle through the list and add each value to the unique list only
        # once.
        for item in lst:
            if unique_lst.count(item) <= 0:
                unique_lst.append(item)

        # Return the list with all redundant values removed.
        return unique_lst

    def _get_values(self, data, attr):
        """
        Creates a list of values in the chosen attribut for each record
        in data, prunes out all of the redundant values, and return
        the list.
        """
        data = data[:]
        return self._unique([record[attr] for record in data])

    def _choose_attribute(self, data, attributes, target_attr):
        """
        Cycles through all the attributes and returns the attribute with the
        highest information gain (or lowest entropy).
        """
        data = data[:]
        best_gain = 0.0
        best_attr = None

        for attr in attributes:
            gain = self._ig.gain(data, attr, target_attr)
            if (gain >= best_gain and attr != target_attr):
                best_gain = gain
                best_attr = attr

        return best_attr

    def _get_examples(self, data, attr, value):
        """
        Returns a list of all the records in <data> with the value of <attr>
        matching the given value.
        """
        data = data[:]
        rtn_lst = []

        if not data:
            return rtn_lst
        else:
            record = data.pop()
            if record[attr] == value:
                rtn_lst.append(record)
                rtn_lst.extend(self._get_examples(data, attr, value))
                return rtn_lst
            else:
                rtn_lst.extend(self._get_examples(data, attr, value))
                return rtn_lst

    def _get_classification(self, record, node=None):
        """
        This function recursively traverses the decision tree and returns a
        classification for the given record.
        """

        if node is None:
            node = self._treedata
        elif not isinstance(node, (dict, list)):
            return node

        attr = node.keys()[0]
        t = node[attr][record[attr]]
        return self._get_classification(record, t)

    def _create_decision_tree(self, data, attributes, target_attr):
        """
        Returns a new decision tree based on the examples given.
        """
        data = data[:]
        vals = [record[target_attr] for record in data]
        default = self._majority_value(data, target_attr)

        # If the dataset is empty or the attributes list is empty, return the
        # default value. When checking the attributes list for emptiness, we
        # need to subtract 1 to account for the target attribute.
        if not data or (len(attributes) - 1) <= 0:
            return default
        # If all the records in the dataset have the same classification,
        # return that classification.
        elif vals.count(vals[0]) == len(vals):
            return vals[0]
        else:
            # Choose the next best attribute to best classify our data
            best = self._choose_attribute(data, attributes, target_attr)

            # Create a new decision tree/node with the best attribute
            # and an empty dictionary object--we'll fill that up next.
            tree = {best: {}}

            # Create a new decision tree/sub-node for each of the values in the
            # best attribute field
            for val in self._get_values(data, best):
                # Create a subtree for the current value under the "best" field
                subtree = self._create_decision_tree(
                    self._get_examples(data, best, val),
                    [attr for attr in attributes if attr != best],
                    target_attr)

                # Add the new subtree to the empty dictionary object in our new
                # tree/node we just created.
                tree[best][val] = subtree

        return tree
