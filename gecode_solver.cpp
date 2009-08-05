#include <Python.h>
#include <iostream>
#include <string.h>
#include "gecode/kernel.hh"
#include "gecode/int.hh"
#include "gecode/search.hh"

#define PM_VERSION(a,b,c) ((a<<16)+(b<<8)+(c))
// There is no easy way to test for gecode version here
// so the build system must pass GE_VERSION accordingly
// by default we build for 3.1.0 if GECODE_VERSION exists

#ifndef GECODE_VERSION
#define GE_VERSION PM_VERSION(2,1,2)
#else
#define GE_VERSION PM_VERSION(3,1,0)
#endif

#if GE_VERSION < PM_VERSION(3,0,0)
#define SELF this
#define SET_VAR_SIZE_MAX SET_VAR_MAX_CARD
#define SET_VAL_MIN_INC SET_VAL_MIN
#else
#define SELF (*this)
#define convexHull convex
#endif

using namespace std;
using namespace Gecode;

class RqlContext {
public:
    RqlContext(long nvars, PyObject* domains,
	       long nvalues, PyObject* constraints, PyObject* sols):
	solutions(-1),
	time(1000),
	fails(-1),
	nvars(nvars),
	nvalues(nvalues),
	constraints(constraints),
	sols(sols),
	domains(domains),
	verbosity(false)
    {
    }

    long solutions;
    long time;
    long fails;
    long nvars;
    long nvalues;
    PyObject* constraints;
    PyObject* sols;
    PyObject* domains;
    bool verbosity;
};

class RqlSolver : public Space {
protected:
    IntVarArray  variables;
public:
    RqlSolver() {}
    RqlSolver(const RqlContext& pb):
	variables(SELF,pb.nvars,0,pb.nvalues-1)
    {
	BoolVar root(SELF, 1,1);
	set_domains( pb.domains );
	add_constraints( pb.constraints, root );
	
	branch(SELF, variables, INT_VAR_NONE, INT_VAL_MIN);
    }

    ~RqlSolver() {};

    RqlSolver(bool share, RqlSolver& s) : Space(share,s)
    {
	variables.update(SELF, share, s.variables);
    }

    void set_domains( PyObject* domains )
    {
	PyObject* ovalues;
	int n = PyList_Size( domains );
	for(int var=0;var<n;++var) {
	    int i, nval;
	    ovalues = PyList_GetItem( domains, var );
	    nval = PyList_Size( ovalues );
	    int* vals = new int[nval];
	    for(i=0;i<nval;++i) {
		vals[i] = PyInt_AsLong( PyList_GetItem( ovalues, i ) );
	    }
	    IntSet gvalues(vals,nval);
	    dom(SELF, variables[var], gvalues);
	    delete [] vals;
	}
    }

    void add_constraints( PyObject* desc, BoolVar& var )
    {
	PyObject* type;
	char* s_type;
	type = PyList_GetItem( desc, 0 );
	s_type = PyString_AsString( type );
	if (strcmp(s_type, "eq")==0) {
	    add_equality( desc, var );
	} else if (strcmp(s_type, "eqv")==0) {
	    add_equivalence( desc, var );
	} else if (strcmp(s_type, "and")==0) {
	    add_and( desc, var );
	} else if (strcmp(s_type, "or")==0) {
	    add_or( desc, var );
	}
    }

    long get_int( PyObject* lst, int index ) {
	PyObject* val;
	val = PyList_GetItem(lst, index);
	return PyInt_AsLong(val);
    }

    void add_equality( PyObject* desc, BoolVar& var ) {
	long variable, value;
	
	variable = get_int( desc, 1 );
	value = get_int( desc, 2 );
	rel(SELF, variables[variable], IRT_EQ, value, var);
    }

    void add_equivalence( PyObject* desc, BoolVar& var ) {
	int len = PyList_Size(desc);
	int var0 = get_int( desc, 1 );

	for (int i=1;i<len-1;++i) {
	    int var1 = get_int(desc, i+1);
	    rel( SELF, variables[var0], IRT_EQ, variables[var1], var );
	}
    }

    void add_and( PyObject* desc, BoolVar& var ) {
	int len = PyList_Size(desc);
	BoolVarArray terms(SELF, len-1,0,1);
	for(int i=0;i<len-1;++i) {
	    PyObject* expr = PyList_GetItem(desc, i+1);
	    add_constraints( expr, terms[i] );
	}
	rel(SELF, BOT_AND, terms, var);
    }

    void add_or( PyObject* desc, BoolVar& var ) {
	int len = PyList_Size(desc);
	BoolVarArray terms(SELF, len-1,0,1);
	for(int i=0;i<len-1;++i) {
	    PyObject* expr = PyList_GetItem(desc, i+1);
	    add_constraints( expr, terms[i] );
	}
	rel(SELF, BOT_OR, terms, var);
    }

    template <template<class> class Engine>
    static void run( RqlContext& pb, Search::Stop* stop )
    {
    double t0 = 0;
    int i = pb.solutions;
    //Timer t;
    RqlSolver* s = new RqlSolver( pb );
    //t.start();
    unsigned int n_p = 0;
    unsigned int n_b = 0;
    if (s->status() != SS_FAILED) {
	n_p = s->propagators();
	n_b = s->branchings();
    }
    Search::Options opts;
    //opts.c_d = pb.c_d;
    //opts.a_d = pb.a_d;
    opts.stop = stop;
    Engine<RqlSolver> e(s, opts);
    delete s;
    do {
	RqlSolver* ex = e.next();
	if (ex == NULL)
	    break;
	ex->print(pb);
	delete ex;
	//t0 = t0 + t.stop();
    } while (--i != 0 && t0 < pb.time);
    Search::Statistics stat = e.statistics();
    if (pb.verbosity) {
	cout << endl;
	cout << "Initial" << endl
	     << "\tpropagators:   " << n_p << endl
	     << "\tbranchings:    " << n_b << endl
	     << endl
	     << "Summary" << endl
	     //<< "\truntime:       " << t.stop() << endl
	     << "\truntime:       " << t0 << endl
	     << "\tsolutions:     " << abs(static_cast<int>(pb.solutions) - i) << endl
	     << "\tpropagations:  " << stat.propagate << endl
	     << "\tfailures:      " << stat.fail << endl
#if GE_VERSION < PM_VERSION(3,0,0)
	     << "\tclones:        " << stat.clone << endl
	     << "\tcommits:       " << stat.commit << endl
#else
	     << "\tdepth:        " << stat.depth << endl
	     << "\tnode:       " << stat.node << endl
#endif

	     << "\tpeak memory:   "
	     << static_cast<int>((stat.memory+1023) / 1024) << " KB"
	     << endl;
    }
    }
    virtual void print(RqlContext& pb) {
	PyObject *tuple, *ival;
	tuple = PyTuple_New( pb.nvars );
	for(int i=0;i<pb.nvars;++i) {
	    ival = PyInt_FromLong( variables[i].val() );
	    PyTuple_SetItem( tuple, i, ival );
	}
	PyList_Append( pb.sols, tuple );
    }
    virtual Space* copy(bool share) {
	return new RqlSolver(share, *this);
    }

};

class FailTimeStop : public Search::Stop {
private:
    Search::TimeStop *ts;
    Search::FailStop *fs;
public:
    FailTimeStop(int fails, int time):ts(0L),fs(0L) {
	if (time>=0)
	    ts = new Search::TimeStop(time);
	if (fails>=0) {
	    fs = new Search::FailStop(fails);
	}
    }
#if GE_VERSION < PM_VERSION(3,1,0)
    bool stop(const Search::Statistics& s) {
	int sigs = PyErr_CheckSignals();
	bool fs_stop = false;
	bool ts_stop = false;
	if (fs) {
	    fs_stop = fs->stop(s);
	}
	if (ts) {
	    ts_stop = ts->stop(s);
	}
	return sigs || fs_stop || ts_stop;
    }
#else
    /* from gecode 3.1.0 */
    bool stop(const Search::Statistics& s, const Search::Options &o) {
	int sigs = PyErr_CheckSignals();
	bool fs_stop = false;
	bool ts_stop = false;
	if (fs) {
	    fs_stop = fs->stop(s,o);
	}
	if (ts) {
	    ts_stop = ts->stop(s,o);
	}
	return sigs || fs_stop || ts_stop;
    }
#endif

    /// Create appropriate stop-object
    static Search::Stop* create(int fails, int time) {
	return new FailTimeStop(fails, time);
    }
};

static void _solve( RqlContext& ctx )
{
    Search::Stop *stop = FailTimeStop::create(ctx.fails, ctx.time);

    RqlSolver::run<DFS>( ctx, stop );
}


static PyObject *
rql_solve(PyObject *self, PyObject *args)
{
    PyObject* sols = 0L;
    PyObject* constraints;
    PyObject* domains;
    long nvars, nvalues;
    sols = PyList_New(0);
    if (!PyArg_ParseTuple(args, "OiO", &domains, &nvalues, &constraints))
        return NULL;
    nvars = PyList_Size(domains);
    RqlContext ctx(nvars, domains, nvalues, constraints, sols );
    _solve( ctx );
    return sols;
}

static PyMethodDef SolveRqlMethods[] = {
    {"solve",  rql_solve, METH_VARARGS,
     "Solve RQL variable types problem."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
initrql_solve(void)
{
    PyObject* m;
    m = Py_InitModule("rql_solve", SolveRqlMethods);
    if (m == NULL)
        return;
}
