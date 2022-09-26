import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Making sure that every value in the variable domain is consistent with unary constraint.
        for var in self.domains.keys():
            domainCopy = self.domains[var].copy()
            for value in domainCopy:
                if len(value) != var.length:
                    self.domains[var].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.
        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        # Making necessary revision in the domain of x to make it consistent with y.
        revision = False
        if self.crossword.overlaps[x,y]:
            removable = []
            xdomainCopy = self.domains[x].copy()
            overlap = self.crossword.overlaps[x,y]
            for xvalue in self.domains[x]:
                for yvalue in self.domains[y]:
                    if xvalue[overlap[0]] == yvalue[overlap[1]]:  
                        if xvalue not in removable:
                            removable.append(xvalue)
            for avalue in xdomainCopy:
                if avalue not in removable:
                    self.domains[x].remove(avalue)
            if xdomainCopy != self.domains[x]:
                revision = True
            
        return revision

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.
        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        # Adding all the arcs if no arcs are provided.
        if not arcs:
            arclist = []
            for a in self.domains:
                for b in self.domains:
                    if a is not b:
                        if self.crossword.overlaps[a,b]:
                            arclist.append((a,b))
        else:
            arclist = arcs

        while not arclist:
            x,y = arclist.pop(0)
            # Revising the particular arc.
            if self.revise(x,y):
                # If any domain's value remains empty then returning false.
                if len(self.domains[x]) == 0:
                    return False
                for eachvalue in self.crossword.neighbors(x):
                    if eachvalue is y:
                        continue
                    arclist.append((eachvalue, x))
        return True 


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # Iterating over the domain's keys to check if the assignment is complete or not.
        for var in self.domains.keys():
            if var not in assignment.keys():
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        values = []
        for var in assignment.keys():
            # Checking the given unary constraint.
            if var.length != len(assignment[var]):
                return False
            
            # Making sure every value is unique.
            if assignment[var] in values:
                return False
            values.append(assignment[var])

            # Iterating over to check the binary constraint.
            for neighbor in self.crossword.neighbors(var):
               overlap = self.crossword.overlaps[var, neighbor]
               if overlap:
                    if neighbor in assignment:
                        if assignment[var][overlap[0]] != assignment[neighbor][overlap[1]]:
                            return False
        return True


    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        count = {}
        returningList = []

        # Iterating over every value in given variable
        for values in self.domains[var]:
            
            count[values] = 0
            neighbor = self.crossword.neighbors(var)
        
            for oneneigbor in neighbor:
                # If already assigned then continue.
                if oneneigbor in assignment:
                    continue

                overlap = self.crossword.overlaps[var,oneneigbor]
                for neigborvalue in self.domains[oneneigbor]:
                    if overlap:
                        # If the value rules out the values for neighbor then adding 1 to the number of neighbor values 
                        # the particular value of the variable rules out.
                        if neigborvalue[overlap[1]] == values[overlap[0]]:
                            count[values] += 1

        # Sorting the count dictionary in terms of the value of count.            
        sorted_order = sorted(count.items(), key=lambda x: x[1], reverse=True)

        for i in sorted_order:
            returningList.append(i[0])

        return returningList

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        count = {}
        neigbor = {}

        # Iterating over the variable in self domain.
        for var in self.domains.keys():
            # If the variable is already assigned then continue.
            if var in assignment:
                continue
            count[var] = 0
            for values in self.domains[var]:
                count[var] += 1
        # Sorting by the minimum remaining value heuristic
        sorted_order = sorted(count.items(), key=lambda x: x[1])
        highestValue = sorted_order[0][1]
        for k,v in count.items():
            if v == highestValue:
                neigbor[k] = 0
                for neigbors in self.crossword.neighbors(k):
                    neigbor[k] += 1
            if v != highestValue:
                continue
        
        # If any two variable has the same value for  minimum remaining value heuristic
        # then sorting them by degree heuristic. 
        sorted_value = sorted(neigbor.items(), key=lambda x: x[1], reverse=True)
        required_variable = sorted_value[0][0]
        return required_variable

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.
        `assignment` is a mapping from variables (keys) to words (values).
        If no assignment is possible, return None.
        """
        # If the assignment is complete, then returning so.
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)
    
        # Iterating over the value in the domain of the variable and recursively backtracking.
        for value in self.order_domain_values(var, assignment):
            assignment[var] = value
            if self.consistent(assignment):
                result = self.backtrack(assignment=assignment)
                if result: 
                    return result
            del assignment[var]
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
