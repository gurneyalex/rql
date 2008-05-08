# -*- coding: utf-8 -*-
# Copyrigth 2000-2008 Logilab S.A. - Paris, France - http://www.logilab.fr <contact@logilab.fr>

"""
x in (A,B,C,D)
y in (A,B,C)
(x == A and y == B) or (x == B and y == C)

sols = (v1:Set1,v2:Set2,...)

sola(v1,v2) | solb(v2,v3) = (v1:Set1,v2:Set2a|Set2b,v3:Set3)
sola(v1,v2) & solb(v2,v3) = (v1:Set1,v2:Set2a&Set2b,v3:Set3)



N1 or N2 : sols = [ s1 for s1 in N1.sols() ] + [ s2 for s2 in N2.sols() ]

N1 and N2 : sols = [ s1&s2 for s1 in N1.sols() for s2 in N2.sols() if s1&s2 not empty ]

V in Set : sols = (V:Set)

"""

import bisect

def intersect_sol(s1, s2):
    sol = s1.copy()
    sol.update(s2)
    
    for n,v in s1.items():
        if sol[n]!=v:
            return {}
    return sol

def empty_sol(s):
    for set in s.values():
        if not set:
            return False


class SolBase(object):

    def __init__(self):
        raise NotImplementedError('override in derived classes')
    
    def and_sols(self, sols1, sols2):
        sols = []
        for s1 in sols1:
            for s2 in sols2:
                s = intersect_sol(s1,s2)
                if s:
                    sols.append( s )
        return sols

    def or_sols(self, sols1, sols2):
        sols = sols1[:]
        for s in sols2:
            if s not in sols:
                sols.append(s)
        return sols
        

    def __and__(self, x):
        return SolAnd(self,x)

    def __or__(self, x):
        return SolOr(self,x)

    def __invert__(self):
        return SolNot(self)

    def __call__(self, domains):
        return self.sols(domains)

    def variables(self, upd=None):
        """Returns a dict whose keys are variables used
        by this formula. if upd is provided it is used
        instead of an empty dict and it keeps already existing
        variables intact"""
        raise NotImplementedError

class SolNot(SolBase):
    
    def __init__(self, s):
        self.sol = s

    def sols(self, domains):
        return self.sol.not_sols(domains)

    def __str__(self):
        return "not ("+str(self.sol)+")"

    def variables(self, upd=None):
        return self.sol.variables(upd)


class SolAnd(SolBase):

    def __init__(self, s1, s2):
        self.sol = []
        self.cost= []
        # optimize (a and b) and c into and(a,b,c)
        if isinstance(s1,SolAnd):
            for s in s1.sol:
                self.insert( s )
        else:
            self.insert(s1)
        # optimize a and (b and c) into and(a,b,c)
        if isinstance(s2,SolAnd):
            for s in s2.sol:
                self.insert( s )
        else:
            self.insert(s2)

    def insert(self, sol):
        N = len(sol.variables())
        idx = bisect.bisect_left(self.cost,N)
        self.cost.insert(idx, N)
        self.sol.insert(idx, sol)
        
    def sols(self, domains):
        sols = self.sol[0](domains)
        for s in self.sol[1:]:
            # domains = restrain(domains,sols)
            S = s(domains)
            sols = self.and_sols( sols, S )
        return sols

    def not_sols(self, domains):
        sols1 = self.s1.not_sols(domains)
        sols2 = self.s2.not_sols(domains)
        return self.or_sols(sols1,sols2)

    def __str__(self):
        rsols = [str(s) for s in self.sol ]
        return "(" + " and ".join(rsols) + ")"

    def variables(self, upd=None):
        if upd is None:
            upd = {}
        for s in self.sol:
            s.variables(upd)
        return upd

class SolOr(SolBase):
    
    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2

    def sols(self, domains):
        sols1 = self.s1.sols(domains)
        sols2 = self.s2.sols(domains)
        return self.or_sols( sols1, sols2 )

    def not_sols(self, domains):
        sols1 = self.s1.not_sols(domains)
        sols2 = self.s2.not_sols(domains)
        return self.and_sols(sols1,sols2)

    def __str__(self):
        return "(" + str(self.s1) + " or " + str(self.s2) + ")"

    def variables(self, upd=None):
        if upd is None:
            upd = {}
        for s in (self.s1,self.s2):
            s.variables(upd)
        return upd

class SolRelation(SolBase):
    """Boolean relation between variables"""
    
    def __init__(self, *variables):
        self._variables = list(variables)

    def variables(self, upd=None):
        if upd is None:
            upd = {}
        for v in self._variables:
            upd[v.var] = 0
        return upd


class SolVar(SolRelation):
    """Simple unary relation True if var in set"""
    
    def __init__(self, V, s):
        self.var = V
        self.set = s

    def variables(self, upd=None):
        if upd is None:
            upd = {}
        upd[self.var] = 0
        return upd

    def sols(self, domains):        
        return [ { self.var : v } for v in self.set if v in domains[self.var] ]

    def not_sols(self, domains):
        return [ { self.var : v } for v in domains[self.var] if v not in self.set ]

    def __str__(self):
        return str(self.var) + " in " + str(self.set)

    def __eq__(self,v):
        return SolEq(self, v)

class SolEq(SolRelation):
    """Simple equality between variables"""
    
    def sols(self, domains):
        d = {}
        # intersect domains
        for var in self._variables:
            for sol in var.sols(domains):
                for v, val in sol.items():
                    c = d.setdefault(val,0)
                    d[val]=c+1
        count = len(self._variables)
        result = []
        for k,v in d.items():
            if v==count:
                r = {}
                for var in self._variables:
                    r[var.var] = k
                result.append( r )
        return result

    def not_sols(self, domains):
        raise NotImplementedError
    
    def __str__(self):
        return "==".join( [v.var for v in self._variables] )
    
    def __eq__(self,v):
        if isinstance(v, SolVar):
            self._variables.append(v)
        elif isinstance(v, SolEq):
            self._variables += v._variables
        else:
            raise RuntimeError("Invalid model")
        return self
        
if __name__ == "__main__":
    # XXX turn this into a test or remove
    D = {
        'x' : range(5),
        'y' : range(6),
        'z' : range(4)
        }
    X = SolVar('x', [1,2,3] )
    Y = SolVar('y', [4,5,6] )
    Z = SolVar('z', [2,3] )
    w0 = (X & Y) | Z
    w1 = X & Y & ( X==Z )
    print w0, w0.sols(D)
    print w1, w1.sols(D)
