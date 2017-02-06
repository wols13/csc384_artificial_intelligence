#Look for #IMPLEMENT tags in this file. These tags indicate what has
#to be implemented to complete the Sokoban warehouse domain.

#   You may add only standard python imports---i.e., ones that are automatically
#   available on TEACH.CS
#   You may not remove any imports.
#   You may not import or otherwise source any of your own files

# import os for time functions
import os
from search import * #for search engines
from sokoban import SokobanState, Direction, PROBLEMS, sokoban_goal_state #for Sokoban specific classes and problems
import math
from scipy.sparse.csgraph import shortest_path
from scipy.optimize import linear_sum_assignment
import numpy as np

#Global Directions
UP = Direction("up", (0, -1))
RIGHT = Direction("right", (1, 0))
DOWN = Direction("down", (0, 1))
LEFT = Direction("left", (-1, 0))

distance_matrix = None
previous_hvals = {}

#SOKOBAN HEURISTICS
def heur_displaced(state):
  '''trivial admissible sokoban heuristic'''
  '''INPUT: a sokoban state'''
  '''OUTPUT: a numeric value that serves as an estimate of the distance of the state to the goal.'''
  count = 0
  for box in state.boxes:
    if box not in state.storage:
      count += 1
  return count

def heur_manhattan_distance(state):
#IMPLEMENT
    '''admissible sokoban heuristic: manhattan distance'''
    '''INPUT: a sokoban state'''
    '''OUTPUT: a numeric value that serves as an estimate of the distance of the state to the goal.'''
    #We want an admissible heuristic, which is an optimistic heuristic.
    #It must always underestimate the cost to get from the current state to the goal.
    #The sum Manhattan distance of the boxes to their closest storage spaces is such a heuristic.
    #When calculating distances, assume there are no obstacles on the grid and that several boxes can fit in one storage bin.
    #You should implement this heuristic function exactly, even if it is tempting to improve it.
    #Your function should return a numeric value; this is the estimate of the distance to the goal.

    sum_manhattan_distance = 0
    valid_storage = state.storage

    for box in state.boxes:
        min_manhattan_distance = math.inf
        if state.restrictions is not None:
            valid_storage = state.restrictions[state.boxes[box]]
        for storage in valid_storage:
            manhattan_distance = abs(box[0] - storage[0]) + abs(box[1] - storage[1])
            min_manhattan_distance = min(manhattan_distance, min_manhattan_distance)
        sum_manhattan_distance += min_manhattan_distance

    return sum_manhattan_distance

def heur_alternate(state):
#IMPLEMENT
    '''a better sokoban heuristic'''
    '''INPUT: a sokoban state'''
    '''OUTPUT: a numeric value that serves as an estimate of the distance of the state to the goal.'''
    #heur_manhattan_distance has flaws.
    #Write a heuristic function that improves upon heur_manhattan_distance to estimate distance between the current state and the goal.
    #Your function should return a numeric value for the estimate of the distance to the goal.

    global distance_matrix
    global previous_hvals
    all_box_storage_distances = []

    if state.index == 1:
        distance_matrix = all_pairs_distance(state)

    if state.parent and state.boxes == state.parent.boxes:
        previous_hvals[state.index] = previous_hvals[state.parent.index]
        return previous_hvals[state.index]

    for box in state.boxes:
        distance_to_all_storages = []
        for store in state.storage:
            if state.restrictions and (store not in state.restrictions[state.boxes[box]]):
                distance_to_all_storages.append(10000)
            else:
                row = (box[0] * state.height) + box[1]
                col = (store[0] * state.height) + store[1]
                distance_to_all_storages.append(distance_matrix[row][col])
        all_box_storage_distances.append(distance_to_all_storages)

    all_box_storage_distances = np.array(all_box_storage_distances)
    row_ind, col_ind = linear_sum_assignment(all_box_storage_distances)
    previous_hvals[state.index] = all_box_storage_distances[row_ind, col_ind].sum()

    return previous_hvals[state.index]


def all_pairs_distance(state):
    no_of_cells = state.width * state.height
    input_matrix = []

    for _ in range(no_of_cells):
        zero_row = [0] * no_of_cells
        input_matrix.append(zero_row)

    for x in range(state.width):
        for y in range(state.height):
            for direction in (UP, RIGHT, DOWN, LEFT):
                neighbour = direction.move((x, y))
                if out_of_bounds(state, neighbour):
                    continue
                row = (x * state.height) + y
                column = (neighbour[0] * state.height) + neighbour[1]
                if neighbour in state.obstacles:
                    input_matrix[row][column] = 10000
                else:
                    input_matrix[row][column] = 1

    input_matrix = np.array(input_matrix)
    return shortest_path(input_matrix, method='auto', directed=True,
                         return_predecessors=False, unweighted=False, overwrite=False)


def out_of_bounds(state, cell):
    if cell[0] < 0 or cell[0] >= state.width:
        return True
    if cell[1] < 0 or cell[1] >= state.height:
        return  True

    return False


def obstacles_encountered(box, obstacles, x_diff, y_diff):
    total_obstacles = 0
    new_box_location = box

    for i in range(abs(x_diff)):
        if x_diff > 0:
            new_box_location = RIGHT.move(new_box_location)
        else:
            new_box_location = LEFT.move(new_box_location)
        if new_box_location in obstacles:
            total_obstacles += 1

    for j in range(abs(y_diff)):
        if y_diff > 0:
            new_box_location = DOWN.move(new_box_location)
        else:
            new_box_location = UP.move(new_box_location)
        if new_box_location in obstacles:
            total_obstacles += 1
    return total_obstacles


def fval_function(sN, weight):
#IMPLEMENT
    """
    Provide a custom formula for f-value computation for Anytime Weighted A star.
    Returns the fval of the state contained in the sNode.

    @param sNode sN: A search node (containing a SokobanState)
    @param float weight: Weight given by Anytime Weighted A star
    @rtype: float
    """

    #Many searches will explore nodes (or states) that are ordered by their f-value.
    #For UCS, the fvalue is the same as the gval of the state. For best-first search, the fvalue is the hval of the state.
    #You can use this function to create an alternate f-value for states; this must be a function of the state and the weight.
    #The function must return a numeric f-value.
    #The value will determine your state's position on the Frontier list during a 'custom' search.
    #You must initialize your search engine object as a 'custom' search engine if you supply a custom fval function.
    return sN.gval + (weight * sN.hval)


def anytime_gbfs(initial_state, heur_fn, timebound = 10):
#IMPLEMENT
    '''Provides an implementation of anytime greedy best-first search, as described in the HW1 handout'''
    '''INPUT: a sokoban state that represents the start state and a timebound (number of seconds)'''
    '''OUTPUT: A goal state (if a goal is found), else False'''

    start_time = os.times()[0]
    new_se = SearchEngine('best_first', 'full')
    new_se.init_search(initial_state, sokoban_goal_state, heur_fn)
    result = new_se.search(timebound)

    #After initial iteration, search for more optimal solution
    temp = result
    while temp and ((timebound - (os.times()[0] - start_time)) > 0):
        temp = new_se.search(timebound - (os.times()[0] - start_time), (temp.gval - 1, math.inf, math.inf))
        if temp:
            result = temp

    return result


def anytime_weighted_astar(initial_state, heur_fn, weight=1., timebound = 10):
#IMPLEMENT
    '''Provides an implementation of anytime weighted a-star, as described in the HW1 handout'''
    '''INPUT: a sokoban state that represents the start state and a timebound (number of seconds)'''
    '''OUTPUT: A goal state (if a goal is found), else False'''

    start_time = os.times()[0]
    new_se = SearchEngine('custom')
    wrapped_fval_function = (lambda sN: fval_function(sN, weight))
    new_se.init_search(initial_state, sokoban_goal_state, heur_fn, wrapped_fval_function)
    result = new_se.search(timebound)

    # After initial iteration, search for more optimal solution
    temp = result
    while temp and ((timebound - (os.times()[0] - start_time)) > 0):
        temp = new_se.search(timebound - (os.times()[0] - start_time), (math.inf, math.inf, temp.gval + heur_fn(temp) - 1))
        if temp:
            result = temp

    return result

if __name__ == "__main__":
  #TEST CODE
  solved = 0; unsolved = []; counter = 0; percent = 0; timebound = 2; #2 second time limit for each problem
  print("*************************************")
  print("Running A-star")

  for i in range(0, 10): #note that there are 40 problems in the set that has been provided.  We just run through 10 here for illustration.

    print("*************************************")
    print("PROBLEM {}".format(i))

    s0 = PROBLEMS[i] #Problems will get harder as i gets bigger

    se = SearchEngine('astar', 'full')
    se.init_search(s0, goal_fn=sokoban_goal_state, heur_fn=heur_displaced)
    final = se.search(timebound)

    if final:
      final.print_path()
      solved += 1
    else:
      unsolved.append(i)
    counter += 1

  if counter > 0:
    percent = (solved/counter)*100

  print("*************************************")
  print("{} of {} problems ({} %) solved in less than {} seconds.".format(solved, counter, percent, timebound))
  print("Problems that remain unsolved in the set are Problems: {}".format(unsolved))
  print("*************************************")

  solved = 0; unsolved = []; counter = 0; percent = 0; timebound = 8; #8 second time limit
  print("Running Anytime Weighted A-star")

  for i in range(0, 10):
    print("*************************************")
    print("PROBLEM {}".format(i))

    s0 = PROBLEMS[i] #Problems get harder as i gets bigger
    weight = 10
    final = anytime_weighted_astar(s0, heur_fn=heur_displaced, weight=weight, timebound=timebound)

    if final:
      final.print_path()
      solved += 1
    else:
      unsolved.append(i)
    counter += 1

  if counter > 0:
    percent = (solved/counter)*100

  print("*************************************")
  print("{} of {} problems ({} %) solved in less than {} seconds.".format(solved, counter, percent, timebound))
  print("Problems that remain unsolved in the set are Problems: {}".format(unsolved))
  print("*************************************")

# if min_manhattan_distance:
#     deadends = 0
#     for direction in (UP, RIGHT, DOWN, LEFT):
#         box_neighbour = direction.move(box)
#         if box_neighbour[0] < 0 or box_neighbour[0] >= state.width:
#             deadends += 1
#         if box_neighbour[1] < 0 or box_neighbour[1] >= state.height:
#             deadends += 1
#         if box_neighbour in state.obstacles: #other robots
#             deadends += 1
#     if deadends > 1:
#         return math.inf


# sum_manhattan_distance = 0
# valid_storage = state.storage
# used_storage = []
#
# for box in state.boxes:
#     min_manhattan_distance = math.inf
#     closest_storage = None
#     if state.restrictions is not None:
#         valid_storage = state.restrictions[state.boxes[box]]
#     valid_storage = list(set(valid_storage) - set(used_storage))
#     for storage in valid_storage:
#         manhattan_distance = abs(box[0] - storage[0]) + abs(box[1] - storage[1])
#         if manhattan_distance < min_manhattan_distance:
#             min_manhattan_distance = manhattan_distance
#             closest_storage = storage
#     if closest_storage:
#         used_storage.append(closest_storage)
#     sum_manhattan_distance += min_manhattan_distance
#
# return sum_manhattan_distance