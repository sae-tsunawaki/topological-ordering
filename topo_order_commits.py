import os
import sys
import zlib
import copy
from collections import deque

class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = []
        self.children = []

def topo_order_commits():
    git_dir = get_git_dir()
    local_branch_heads = local_branch_names()
    commit_nodes = build_commit_graph(git_dir, local_branch_heads)
    topo_ordered_commits = topological_sort(commit_nodes)
    head_to_branches = local_branch_heads
    print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, head_to_branches)

# find the .git directory 
def get_git_dir():
    current_dir = os.getcwd()
    while (current_dir != '/'): 
        # if .git is in the cwd, return the path with the .git
        if (os.path.isdir(current_dir + '/.git')):
            return current_dir + '/.git'
        current_dir = os.path.dirname(current_dir)
    sys.stderr.write('Not inside a Git repository')
    exit(1)

# get the list of local branch names
def local_branch_names():
    # find all branches inside refs/heads folder 
    branch_dir = os.path.join(get_git_dir(),'refs','heads')
    branches = []

    for root, dirs, files in os.walk(branch_dir):
        for f in files: 
            fullpath = os.path.join(root, f)
            branch = fullpath[len(branch_dir)+1:]
            branches.append(branch)
    
    # find corresponding commit hashes 
    branch_commit_hash = dict()
    for branch in branches:
        file_name = os.path.join(branch_dir, branch)
        if os.path.isfile(file_name):
            commit_hash = open(file_name, 'r').readline().strip()
            if branch in branch_commit_hash:
                branch_commit_hash[commit_hash].append(branch)
            else:
                branch_commit_hash[commit_hash] = branch
    
    return branch_commit_hash

# build the commit graph 
def build_commit_graph(git_dir, local_branch_heads):
    commit_nodes = {} # represents your graph 
    visited = set()
    branch_contents = local_branch_names()
    stack = []
    for x in branch_contents:
        stack.append(x)

    while stack:
        # store next element in commit_hash, and remove from stack
        commit_hash = stack.pop()
        if commit_hash in visited:
            continue
        visited.add(commit_hash)
        if commit_hash not in commit_nodes:
            # create a commit node and store it in the graph for later use 
            new_commit_node = CommitNode(commit_hash)
            commit_nodes[commit_hash] = new_commit_node

        # retrieve commit node object from graph 
        commit = commit_nodes[commit_hash]

        # get parent commits 
        os.chdir(git_dir + '/objects')
        commit_dir = os.getcwd()
        commit_file = commit_dir + '/' + commit_hash[:2] + '/' + commit_hash[2:]
        open_commit_file = open(commit_file, 'rb').read()
        decomp_commit_file = zlib.decompress(open_commit_file).decode()

        #split contents and save line(s) containing parent hashes 
        split_file = decomp_commit_file.split()
        i = 0 
        for x in split_file:
            if (x == 'parent'):
                commit.parents.append(split_file[i+1])
            i = i + 1

        for p in commit.parents:
            if p not in visited:
                stack.append(p)
            if p not in commit_nodes:
                #create parent node and add to the graph 
                new_parent_node = CommitNode(p)
                commit_nodes[p] = new_parent_node
            # record that commit hash is a child of commit node p
            commit_nodes[p].children.append(commit_hash)

    return commit_nodes

def topological_sort(commit_nodes):
    result = [] # processed and sorted commits
    no_children = deque() # commits we can process now 
    copy_graph = copy.deepcopy(commit_nodes) # copy graph to not lose info 

    # if the commit has no children, we can process it 
    for commit_hash in copy_graph:
        if len(copy_graph[commit_hash].children) == 0:
            no_children.append(commit_hash)

    # loop through until all commits are processed 
    while len(no_children) > 0:
        commit_hash = no_children.popleft()
        result.append(commit_hash)

        # now that we are processing commit, remove all connecting edges to parent commits 
        # and add parent to processing set if it has no more children after 
        for parent_hash in list(copy_graph[commit_hash].parents):
            # remove parent hash from current commit parents 
            copy_graph[commit_hash].parents.remove(parent_hash)
            # remove child hash from parent commit children 
            copy_graph[parent_hash].children.remove(commit_hash)
            # check parent has no children 
            if len(copy_graph[parent_hash].children) == 0:
                no_children.append(parent_hash)
    
    # error check at the end 
    if len(result) < len(commit_nodes):
        raise Exception("cycle detected")
    return result 

# print commit hashes 
def print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, head_to_branches):
    jumped = False
    for i in range(len(topo_ordered_commits)):
        commit_hash = topo_ordered_commits[i]
        if jumped:
            jumped = False
            sticky_hash = ' '.join(commit_nodes[commit_hash].children)
            print(f'={sticky_hash}')
        branches = sorted(head_to_branches[commit_hash]) if commit_hash in head_to_branches else []
        print(commit_hash + (' ' + ' '.join(branches) if branches else ' '))
        if i+1 < len(topo_ordered_commits) and topo_ordered_commits[i+1] not in commit_nodes[commit_hash].parents:
            jumped = True 
            sticky_hash = ' '.join(commit_nodes[commit_hash].parents)
            print(f'{sticky_hash}=\n')
    

if __name__ == '__main__':
    topo_order_commits()
