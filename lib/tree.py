'''
A dummy implementation of decision trees
'''

from lib.node import Node
from lib.exceptions import *
import numpy as np
import pandas as pd
import pickle, os
class Tree:

    '''
    params:
    train_data - training data to trainthe tree
    depth - max recursion depth of the tree
    benchmark - benchmark for geni/entropy
    '''
    def __init__(self, data, depth, benchmark, rows, features, cat_features, user_input=False): #should we include data here
        self.depth = depth
        self.rows = rows
        self.features = features
        self.data = data
        self.benchmark = benchmark
        self.head = Node(data, rows, features, 0, depth, cat_features, None, user_input=user_input)
        self.oob_error = -1
        self.cat_features = cat_features
        self.user_input = user_input

    def visualize(self):
        if not os.path.exists('vis'):
            os.makedirs('vis')
        cur = self.head
        to_put = []
        nodes = [cur]
        depth = 0
        while len(nodes) > 0:
            children = []
            for node in nodes:
                if node.left or node.right:
                     to_put.append('{ID} [label="X[{min_feature}] < {min_break}\ngini = {min_gini}\nsamples = {rows}\ndistribution = [{left}, {right}]"];'.format(ID=node.id, min_feature=node.min_feature, min_break=node.min_break_point, min_gini=node.min_gini, rows=len(node.rows), left=len(node.left.rows), right=len(node.right.rows)))
                else:
                     to_put.append('{ID} [label="samples = {rows}\nratio = [{left}, {right}]"];'.format(ID=node.id, rows=len(node.rows), left=node.get_proportions('0'), right=node.get_proportions('1')))
                if node.parent_id != None:
                    if node.side == 'l':
                        to_put.append('{} -> {} [labeldistance=8, labelangle=30, xlabel="True"]'.format(node.parent_id, node.id))
                    else:
                        to_put.append('{} -> {} [labeldistance=8, labelangle=-30, xlabel="False"]'.format(node.parent_id, node.id))
                if node.left:
                    children.append(node.left)
                if node.right:
                    children.append(node.right)
            nodes = children
        joined = "digraph Tree {\nnode [shape=box];\n" + "\n".join(to_put) + "\n}"
        with open("vis/tree.dot", "w") as f:
            f.write(joined)
        return joined

    '''
    Recursively split until geni/entropy benchmark met or max_depth reached
    '''
    def fit(self):
        #think about behavior of pure nodes more
        try:
            self.head = self.head.split()
        except (ValueError, CannotDistinguishException) as e: #change this to whatever node.split() throws
            # TODO: fix error handling for no-more-split cases more better
            print(e)
            print("oops")
            pass
        return self


    '''
    params:
    test_data - test data to run the prediction on
    visualize - if True, runs the parts of the code responsible for visualization
    imporance - if True, also returns feature importances for predicting each value
    return:
    confidence/probability of each category
    id of each document
    feature_importances (optional) - [{feature:prediction_weight}]
        where feature is a column and prediction_weight is the amount that this feature shifted the relevant confidence
        (a positive value suggests that this feature implies relevance, and a negative value suggests the opposite).

    TODO: the current toggling mechanism for visualization is super clunky. Maybe we
          can improve on it down the line
    '''
    def predict(self, test_data, visualize=False, importance=False):
        #         assuming input data is a dataframe right now
        confidences = []
        feature_importances = [] #dict from featurename: (rel_bias, irrel_bias)
        ids = []

        if visualize:
            if not os.path.exists('vis'):
                os.makedirs('vis')

        for index, row in test_data.iterrows():
            node_path = []
            lefts = [] #True if we go left, False otherwise
            cur_feat_imp = {}

            if visualize:
                to_put = []

            cur_node = self.head
            while (cur_node.left and cur_node.right):
                if importance:
                    node_path.append(cur_node)
                if cur_node.left or cur_node.right:
                    if visualize:
                        to_put.append('{ID} [label="X[{min_feature}] < {min_break}\n'
                                      + 'gini = {min_gini}\nsamples = {rows}\n'
                                      + 'distribution = [{left}, {right}]"];'.format(ID=cur_node.id,
                                                                                     min_feature=cur_node.min_feature,
                                                                                     min_break=cur_node.min_break_point,
                                                                                     min_gini=cur_node.min_gini,
                                                                                     rows=len(cur_node.rows),
                                                                                     left=len(cur_node.left.rows),
                                                                                     right=len(cur_node.right.rows)))
                else:
                    if visualize:
                        to_put.append('{ID} [idx_trees_to_retrainlabel="samples = {rows}\n'
                                      + 'ratio = [{left}, {right}]"];'.format(ID=cur_node.id,
                                                                              rows=len(cur_node.rows),
                                                                              left=cur_node.get_proportions('0'),
                                                                              right=cur_node.get_proportions('1')))

                if cur_node.parent_id != None:
                        if cur_node.side == 'l':
                            if visualize:
                                to_put.append('{} -> {} [labeldistance=8, labelangle=30, '
                                              + 'xlabel="True"]'.format(cur_node.parent_id, cur_node.id))
                        else:
                            if visualize:
                                to_put.append('{} -> {} [labeldistance=8, labelangle=-30, '
                                              + 'xlabel="False"]'.format(cur_node.parent_id, cur_node.id))

                if self._should_go_left(row, cur_node):
                    cur_node = cur_node.left
                    if importance:
                        lefts.append(True)
                else:
                    cur_node = cur_node.right
                    if importance:
                        lefts.append(False)
            if importance:
                node_path.append(cur_node)
                feature_importances.append(self._get_feature_importance(node_path, lefts))

            relevant_confidence = cur_node.get_proportions('1')
            irrelevant_confidence = cur_node.get_proportions('0')
            ids.append(row["ID"])
            confidences.append( (relevant_confidence, irrelevant_confidence) )

            if visualize:
                joined = "digraph Tree {\nnode [shape=box];\n" + "\n".join(to_put) + "\n}"
                with open("vis/{}_predict_vis.dot".format(index), "w") as f:
                    f.write(joined)
        if importance:
            return confidences, ids, feature_importances
        return confidences, ids

    '''
    Predicts the labels of test_data, and returns some information about how the tree came to those predictions.
    params:
    test_data - a pandas df with the same columns as the train_data. Each row is considered to be one sample to predict.
    returns:
    confidences - [(relevant_confidence_doc1, irrelevant_confidence_doc1), (relevant_confidence_doc2...)...]
        where relevant_confidence_doc1 is the confidence this tree has in the first row being a relevant document,
        and irrelevant_confidence_doc1 is the confidence this tree has in the first row being an irrelevant document.
    feature_importances - [{feature:prediction_weight}]
        where feature is a column and prediction_weight is the amount that this feature shifted the relevant confidence
        (a positive value suggests that this feature implies relevance, and a negative value suggests the opposite).
    '''
    def predict_with_feat_imp(self, test_data):
        confidences = []
        feature_importances = [] #dict from featurename: (rel_bias, irrel_bias)
        for index, row in test_data.iterrows():
            node_path = []
            lefts = [] #True if we go left, False otherwise
            cur_feat_imp = {}
            cur_node = self.head
            while (cur_node.left and cur_node.right):
                node_path.append(cur_node)
                if self._should_go_left(row, cur_node):
                    cur_node = cur_node.left
                    lefts.append(True)
                else:
                    cur_node = cur_node.right
                    lefts.append(False)
#         here, cur_node should be the leaf
            node_path.append(cur_node)
            relevant_confidence = cur_node.get_proportions('1')
            irrelevant_confidence = cur_node.get_proportions('0')
            confidences.append((relevant_confidence, irrelevant_confidence))
            feature_importances.append(self._get_feature_importance(node_path, lefts))

        return confidences, feature_importances

    '''
    Given a path taken through this tree, return a dictionary labeling each feature by its prediction
    params:
    node_path - list of Node objects that we've traversed through
    lefts - a list of booleans representing whether we went left or right after node_path[i].
        len(lefts) == len(node_path) - 1
        lefts[i] iff node_path[i].left == node_path[i+1]
        !lefts[i] iff node_path[i].right == node_path[i+1]
    returns:
    features - {feature: prediction weight}, where a large positive value suggests that this feature means
        the item is relevant, and a large negative value suggests the opposite.
    '''
    def _get_feature_importance(self, node_path, lefts):
        features = {}
        # print(node_path)
        for before_split_ind in range(len(node_path) - 1):
            before = node_path[before_split_ind]
            after = node_path[before_split_ind + 1]
            before_prop = before.get_proportions('1')
            after_prop = after.get_proportions('1')
            high_low = "_low" if lefts[before_split_ind] else "_high"
            # features[str(before.min_feature) + high_low] = after_prop - before_prop
            features[str(before.min_feature)] = after_prop - before_prop
        return features

    '''
    helper function to determine which way we should traverse through the tree.
    params:
    row - arraylike from the test data. Should have the same length as the training data.
    cur_node - the node that we are currently on.
    return:
    true if row's value is the same as cur_node's categorical breakpoint, or less than
        cur_node's numerical breakpoint
    false otherwise
    '''
    def _should_go_left(self, row, cur_node):
        if cur_node.min_feature in self.cat_features:
            return row[cur_node.min_feature] == cur_node.min_break_point
        if cur_node.min_feature == 'Date':
            print('{} vs {}'.format(row[cur_node.min_feature], cur_node.min_break_point)) 
        return row[cur_node.min_feature] < cur_node.min_break_point

    '''
    params:
    more_data - more training data to update the tree
    return:
    Null or we can say something like which nodes are changed
    '''
    def update(self, updated_data, new_rows):

        nodes = [self.head]
        node_count = 0
        while (True):
            temp = nodes
            nodes = []
            for node in temp:
                # debugging: check how many nodes this sees
                node_count += 1


                node.data = updated_data
                node.rows = []
                node.proportions = {}
                if node.left:
                    nodes.append(node.left)
                if node.right:
                    nodes.append(node.right)
            if nodes == []:
                break

        # debugging: how many nodes go through the resetting process?
#         print('tree.update: resetted {} nodes'.format(node_count))
        # debugging: how does this compare to number of nodes that exist in the tree?
#         print('tree.update: traverse returned {} nodes.'.format(len(self.traverse())))

        # traverse each new data point through the tree, append row to each node
        for index, row in updated_data.loc[new_rows].iterrows():
            cur_node = self.head
            while (cur_node.left and cur_node.right):
                cur_node.rows = np.append(cur_node.rows, row.name)
                # if it is catagorical, traverse a little differently
                if (cur_node.min_feature in cur_node.cat_features):
                    # members that match go left, others go right.
                    if (cur_node.min_break_point in row[cur_node.min_feature]):
                        cur_node = cur_node.left
                    else:
                        cur_node = cur_node.right
                # for continuous features, just do a simple inequality
                else:
                    if (row[cur_node.min_feature] < cur_node.min_break_point):
                        cur_node = cur_node.left
                    else:
                        cur_node = cur_node.right
            # don't forget about that one last leaf!
            cur_node.rows = np.append(cur_node.rows, row.name)


        t = self.traverse()
        num_rows = [len(r.rows) for r in t]
        empty_nodes = [r for r in t if len(r.rows) == 0]
        for e in empty_nodes:
            if e.parent_node:
                parent = e.parent_node
                if parent.left == e:
                    parent.left = None
                elif parent.right == e:
                    parent.right = None
                else:
                    print('should not be here')
            else:
                # the empty node is a head
                print('this is a head')

        # after updating, look for empty nodes, and reshape tree accordingly.
        nodes_to_traverse = [self.head]
        done = False
        while(not done):
            temp = nodes_to_traverse
            nodes_to_traverse = []
            for i in range(len(temp)):
                # if the current node has children, perform the rebalancing process
                cur = temp[i]
                left = cur.left
                right = cur.right
                parent = cur.parent_node
                if left and right:
                    left_empty = False
                    right_empty = False
                    if (len(left.rows) == 0):
                        left_empty = True
                    else:
                        nodes_to_traverse.append(left)

                    if (len(right.rows) == 0):
                        right_empty = True
                    else:
                        nodes_to_traverse.append(right)

                    if left_empty and right_empty:
                        # if both children are empty, become a leaf node
                        print('both children are empty: this really shouldn\'t have happened')
                        left = None
                        right = None
                    elif left_empty:
#                         print('left empty only')
                        # if only left child is empty, make self into right child
                        if cur == self.head:
#                             print('i need to become my right child, but I am also head')
                            self.head = right
                        elif parent.left == cur:
#                             print('1')
#                             print("parent's left becomes temp's right")
                            parent.left = right
                        else:
#                             print('2')
#                             print("parent's right becomes temp's left")
                            parent.right = right
#                         print('check: temp[i].parent_node.right == temp[i].right: {}'.format(temp[i].parent_node.right == temp[i].right))
                        nodes_to_traverse.append(right)
                        nodes_to_traverse.append(parent)
                        nodes_to_traverse.append(parent.parent_node)



                    elif right_empty:
#                         print('right empty only')
                        # if only right child is empty, make self into left child
                        if cur == self.head:
#                             print('i need to become my left child, but I am also head')
                            self.head = left
                        elif parent.left == cur:
                            parent.left = left
                        else:
                            parent.right = left
                        nodes_to_traverse.append(left)
                        nodes_to_traverse.append(parent)

                    # debugging: checking what this condition would be, or if it ever happens
                    else:
                        pass
#                         print('')
                elif temp[i].left:
#                     print('node has left child but no right')
                    # this is to cover the case where a collapsed node needs to collapse again
                    if len(temp[i].left.rows) == 0:
                        temp[i] = temp[i].left
                        nodes_to_traverse.append(temp[i])
                elif temp[i].right:
#                     print('node has right child but no left')
                    # same but with the right side
                    if len(temp[i].right.rows) == 0:
                        temp[i] = temp[i].left
                        nodes_to_traverse.append(temp[i])
                else:
#                     print('len(cur.rows) == 0?: {}'.format(len(cur.rows) == 0))
#                     print('What is this one? check this one out too')
                    # this node is a leaf, no need to look
                    pass

            if len(nodes_to_traverse) == 0:
                done = True

        t = self.traverse()
#         empty_nodes = [n for n in t if len(n.rows) == 0]
#         print('there are {} empty nodes'.format(len(empty_nodes)))
#         for e in empty_nodes:
#             print('{}th empty node'.format(empty_nodes.index(e)))
#             print('has left: {}'.format(e.left != None))
#             print('has right: {}'.format(e.right != None))
#             print('has parent: {}'.format(e.parent_node != None))
#             print('is head: {}'.format(e == self.head))

#             print('parent has {} rows'.format(len(e.parent_node.rows)))
#             if e.parent_node.left == e:

#                 print('neighbor has {} rows'.format(len(e.parent_node.right.rows)))
#             else:
#                 print('neighbor has {} rows'.format(len(e.parent_node.left.rows)))



        num_rows = [len(r.rows) for r in t]
        if 0 in num_rows:
            print('Warning: after restructuring: there is a 0-row node')
#             print('after restructuring, there are {} nodes in the tree'.format(len(t)))
#             pass

    def traverse(self):
        '''Traverse down the tree and return all of the nodes in a list'''
        nodes_list = [self.head]
        while True:
            initial_size = len(nodes_list)
            for n in nodes_list:
                if n.left:
                    if n.left not in nodes_list:
                        nodes_list.append(n.left)
                        break
                if n.right:
                    if n.right not in nodes_list:
                        nodes_list.append(n.right)
                        break
            if len(nodes_list) == initial_size:
                break
        return nodes_list



    '''
    return:
    The number of ignored data pieces that we get incorrect (n) divided by the number of rows we ignored (l)
    That is, n/l
    '''
    def calc_oob_error(self):
        #complement of rows
        test_data = self.data.loc[~self.data.index.isin(self.rows)]
        complement = set(self.data.index.values.tolist()) - set(self.rows)
        #predict each of those (TODO: update this once we have batch training)
        num_incorrect = 0

        ## batch version of calculating oob error
        # rows in the complement:
        cases = self.data.loc[list(complement)]
        predictions = self.predict(cases)
        for p in range(len(predictions[0])):
            p_id = predictions[1][p]
            p_pred = predictions[0][p]
            # input row for this prediction
            r = self.data.loc[self.data['ID'] == p_id]
            if self.user_input:
                column = 'Relevant'
            else:
                column = 'Label'
            if p_pred[0] > p_pred[1]: # system said it was relevant
                num_incorrect += 1 if r[column].values[0] == '0' else 0
            else: # system said it was irrelevant
                num_incorrect += 1 if r[column].values[0] == '1' else 0

        if len(test_data) < 1:
            print("oh no!")
            self.oob_error = .5
        else:
            self.oob_error = num_incorrect / len(test_data)
#         self.oob_error = num_incorrect / len(complement)
        return self.oob_error

    def store_tree(self, file_path):
        f = open('file_path', 'wb')
        pickle.dump(self, f)
        f.close()


    def load_tree(self, file_path):
        f = open('file_path', 'rb')
        temp = pickle.load(f)
        f.close()

        # reinitialize some variables
        self.__init__(temp.data, temp.depth, temp.benchmark, temp.rows, temp.features)
        # reassign the head
        self.head = temp.head

    '''
    String representation
    '''
    def __str__(self):
        string = ''
        string += str(sorted(self.features))
        string += '\n'
        nodes = [self.head]
        while(len(nodes) > 0):
            new_nodes = []
            level_str = ''
            for node in nodes:
                level_str += str(node) + "\n"
                if node.left:
                    new_nodes.append(node.left)
                if node.right:
                    new_nodes.append(node.right)
            string += level_str+"\n--------------------------------------------------\n"
            nodes = new_nodes
        return string

    '''
    Get MDI value for this tree
    as per this paper:
    https://papers.nips.cc/paper/4928-understanding-variable-importances-in-forests-of-randomized-trees.pdf
    returns: {feature: MDI component for this tree}
    '''
    def get_mean_decrease_impurity(self):
        return self._mdi_helper(self.head)

    '''
    helper function to recursively iterate through the tree to calculate mean decrease impurity.
    '''
    def _mdi_helper(self, curr):
        #return empty dict (no features to split) if leaf
        if curr.left is None and curr.right is None:
            return {}

        #get own decrease
        curr_prop = len(curr.rows)/len(self.rows)
        delta = curr_prop * Tree.calculate_impurity_decrease(curr)

        #get dicts for left and right
        left_decreases = self._mdi_helper(curr.left)
        right_decreases = self._mdi_helper(curr.right)

        #build joined dict
        curr_decrease = {str(curr.min_feature): delta}

        return Tree._join_mdi_dicts(Tree._join_mdi_dicts(curr_decrease, left_decreases), right_decreases)
    '''
    calculates the impurity decrease as per page 2 of
    https://papers.nips.cc/paper/4928-understanding-variable-importances-in-forests-of-randomized-trees.pdf
    '''
    def calculate_impurity_decrease(node):
        left_prop = len(node.left.rows)/len(node.rows)
        right_prop = len(node.right.rows)/len(node.rows)
        delta = node.calc_gini_index() - (left_prop * node.left.calc_gini_index()) - (right_prop * node.right.calc_gini_index())
        return delta

    '''
    returns a copy of all the elements of d1 and d2
    where d1 and d2 share keys, the values are summed
    '''
    def _join_mdi_dicts(d1, d2):
        ans = d1.copy()
        for key in d2.keys():
            try:
                ans[key] += d2[key]
            except KeyError:
                ans[key] = d2[key]
        return ans
