#include "gecode/int.hh"
#include "gecode/kernel.hh"
#include "gecode/search.hh"
#include <Python.h>
#include <exception>
#include <iostream>
#include <string.h>

#if 1
#define debug(fmt, ...)
#else
#define debug(fmt, ...) printf(fmt, ##__VA_ARGS__)
#endif

#define PM_VERSION(a, b, c) ((a << 16) + (b << 8) + (c))
// There is no easy way to test for gecode version here
// so the build system must pass GE_VERSION accordingly
// by default we build for 3.1.0 if GECODE_VERSION exists

#ifndef GE_VERSION
#ifndef GECODE_VERSION
#define GE_VERSION PM_VERSION(2, 1, 2)
#else
#define GE_VERSION PM_VERSION(3, 1, 0)
#endif
#endif

#if GE_VERSION < PM_VERSION(2, 0, 0)
#define SELF this
#define INT_VAR_NONE BVAR_NONE
#define INT_VAL_MIN BVAL_MIN

#elif GE_VERSION < PM_VERSION(3, 0, 0)
#define SELF this
#define SET_VAR_SIZE_MAX SET_VAR_MAX_CARD
#define SET_VAL_MIN_INC SET_VAL_MIN
#else
#define SELF (*this)
#define convexHull convex
#endif

#if GE_VERSION >= PM_VERSION(4, 0, 0)
#define INT_VAR_NONE INT_VAR_NONE()
#define INT_VAL_MIN INT_VAL_MIN()
#endif

using namespace std;
using namespace Gecode;

#define USE_CLOCK
#ifdef USE_CLOCK
#include <ctime>

/// Timer interface stolen from gecode examples
class Timer {
  private:
    clock_t t0;

  public:
    void start(void);
    double stop(void);
};

forceinline void Timer::start(void) { t0 = clock(); }

forceinline double Timer::stop(void) {
    return (static_cast<double>(clock() - t0) / CLOCKS_PER_SEC) * 1000.0;
}
#else
#include <sys/time.h>
#include <unistd.h>

/// Timer interface stolen from gecode examples
class Timer {
  private:
    struct timeval t0;

  public:
    void start(void);
    double stop(void);
};

forceinline void Timer::start(void) { gettimeofday(&t0, NULL); }
forceinline double Timer::stop(void) {
    struct timeval t1;
    gettimeofday(&t1, NULL);
    return (t1.tv_sec - t0.tv_sec) + 1e-6 * (t1.tv_usec - t0.tv_usec);
}
#endif

enum { _AND = 0, _OR = 1, _EQ = 2, _EQV = 3 };

class RqlError : public exception {};

class RqlContext {
    /** Context holding the problem for solving Rql constraints
    we keep the info as Python objects and parse the problem
    during the creation of the Gecode problem
  */
  public:
    RqlContext(long nvars, PyObject *domains, long nvalues,
               PyObject *constraints,
               PyObject *sols)
        : solutions(-1),            // return every solutions
          time(-1),                 // time limit in case the problem is too big
          fails(-1),                // ?? used by GecodeStop ...
          nvars(nvars),             // Number of variables
          nvalues(nvalues),         // Number of values
          constraints(constraints), // A python list, holding the root of
                                    // the problem
          sols(sols),       // an empty list that will receive the solutions
          domains(domains), // A PyList of PyList, one for each var,
                            // holding the allowable integer values
          verbosity(false)  // can help debugging
    {}

    long solutions;
    long time;
    long fails;
    long nvars;
    long nvalues;
    PyObject *constraints;
    PyObject *sols;
    PyObject *domains;
    bool verbosity;
};

class RqlSolver : public Space {
    /* A gecode Space
  this is a strange beast that requires special methods and
  behavior (mostly, copy and (bool,share,space) constructor
  */
  protected:
    /* The variables we try to find values for
   these are the only 'public' variable of the
   problem.

   we use a lot more intermediate variables but
   they shouldn't be member of the space
  */
    IntVarArray variables;

  public:
    RqlSolver(const RqlContext &pb)
        : variables(SELF, // all gecode variable keep a reference to the space
                    pb.nvars,       // number of variables
                    0,              // minimum domain value
                    pb.nvalues - 1) // max domain value (included)
    {
        /* Since we manipulate Boolean expression and
    we need to assign truth value to subexpression
    eg (a+b)*(c+d) will be translated as :
    root = x1 * x2
    x1 = a+b
    x2 = c+d
    root = True
    */
        BoolVar root(SELF, 1, 1);

        set_domains(pb.domains);
        add_constraints(pb.constraints, root);

        /* the branching strategy, there must be one,
    changing it might improve performance, but
    in out case, we almost never propagate (ie
    gecode solves the problem during its creation)
    */
        branch(SELF, variables, INT_VAR_NONE, INT_VAL_MIN);
    }

    ~RqlSolver(){};
#if GE_VERSION < PM_VERSION(6,0,0)
    RqlSolver(bool share, RqlSolver &s) : Space(share, s) {
        /* this is necessary for the solver to fork space
    while branching
    */
        variables.update(SELF, share, s.variables);
    }
#else
    RqlSolver(RqlSolver &s) : Space(s) {
        /* this is necessary for the solver to fork space
    while branching
    */
        variables.update(SELF, s.variables);
    }
#endif

    void set_domains(PyObject *domains) {
        PyObject *ovalues;
        if (!PyList_Check(domains)) {
            throw RqlError();
        }
        int n = PyList_Size(domains);
        for (int var = 0; var < n; ++var) {
            /* iterate of domains which should contains
      list of values
      domains[0] contains possible values for var[0]...
      */
            int i, nval;
            ovalues = PyList_GetItem(domains, var);
            if (!PyList_Check(ovalues)) {
                throw RqlError();
            }
            nval = PyList_Size(ovalues);

            /* It's a bit cumbersome to construct an IntSet, but
      it's the only way to reduce an integer domain to
      a discrete set
      */
            int *vals = new int[nval];
            for (i = 0; i < nval; ++i) {
                // refcount ok, borrowed ref
                vals[i] = PyLong_AsLong(PyList_GetItem(ovalues, i));
                if (vals[i] < 0) {
                    /* we don't have negative values and
          PyInt_AsLong returns -1 if the object is not an
          Int */
                    delete[] vals;
                    throw RqlError();
                }
            }
            IntSet gvalues(vals, nval);
            dom(SELF, variables[var], gvalues);
            delete[] vals;
        }
    }

    /* Dispatch method from Node to specific node type */
    void add_constraints(PyObject *desc, BoolVar &var) {
        long type;

        if (!PyList_Check(desc)) {
            throw RqlError();
        }
        /* the first element of each list (node) is
    a symbolic Int from _AND, _OR, _EQ, _EQV
    */
        type = PyLong_AsLong(PyList_GetItem(desc, 0));

        switch (type) {
        case _AND:
            add_and(desc, var);
            break;
        case _OR:
            add_or(desc, var);
            break;
        case _EQ:
            add_equality(desc, var);
            break;
        case _EQV:
            add_equivalence(desc, var);
            break;
        default:
            throw RqlError();
        }
    }

    /* retrieve an int from a list, throw error if int is <0 */
    long get_uint(PyObject *lst, int index) {
        PyObject *val;
        val = PyList_GetItem(lst, index);
        if (val < 0) {
            throw RqlError();
        }
        return PyLong_AsLong(val);
    }

    /* post gecode condition for Var == Value
   we can't use domain restriction since this
   condition can be part of an OR clause

   so we post  (var == value) <=> expr_value
  */
    void add_equality(PyObject *desc, BoolVar &expr_value) {
        long variable, value;

        variable = get_uint(desc, 1);
        value = get_uint(desc, 2);
        if (variable == 1) {
            debug("RQL:%ld == %ld ***\n", variable, value);
        } else {
            debug("RQL:%ld == %ld\n", variable, value);
        }
        rel(SELF, variables[variable], IRT_EQ, value, expr_value);
    }

    /* post gecode condition for Var[i] == Var[j] ... == Var[k]

   there's no operator for assigning chained equality to boolean

   so we post for 1<=i<=N (var[0] == var[i]) <=> bool[i]
              and    bool[1] & ... & bool[N] <=> expr_value
   that means if all vars are equal expr_value is true
   if all vars are different from var[0] expr_value is false
   if some are equals and some false, the constraint is unsatisfiable
  */
    void add_equivalence(PyObject *desc, BoolVar &expr_value) {
        int len = PyList_Size(desc);
        int var0 = get_uint(desc, 1);
        BoolVarArray terms(SELF, len - 2, 0, 1);
        debug("RQL:EQV(%d", var0);
        for (int i = 1; i < len - 1; ++i) {
            int var1 = get_uint(desc, i + 1);
            debug(",%d", var1);
            rel(SELF, variables[var0], IRT_EQ, variables[var1], terms[i - 1]);
        }
        debug(")\n");
#if GE_VERSION < PM_VERSION(2, 0, 0)
        BoolVarArgs terms_args(terms);
        bool_and(SELF, terms_args, expr_value);
#else
        rel(SELF, BOT_AND, terms, expr_value);
#endif
    }

    /* simple and relation between nodes */
    void add_and(PyObject *desc, BoolVar &var) {
        int len = PyList_Size(desc);
        BoolVarArray terms(SELF, len - 1, 0, 1);

        debug("RQL:AND(\n");
        for (int i = 0; i < len - 1; ++i) {
            PyObject *expr = PyList_GetItem(desc, i + 1);
            add_constraints(expr, terms[i]);
        }
        debug("RQL:)\n");
#if GE_VERSION < PM_VERSION(2, 0, 0)
        BoolVarArgs terms_args(terms);
        bool_and(SELF, terms_args, var);
#else
        rel(SELF, BOT_AND, terms, var);
#endif
    }

    /* simple or relation between nodes */
    void add_or(PyObject *desc, BoolVar &var) {
        int len = PyList_Size(desc);
        BoolVarArray terms(SELF, len - 1, 0, 1);

        debug("RQL:OR(\n");
        for (int i = 0; i < len - 1; ++i) {
            PyObject *expr = PyList_GetItem(desc, i + 1);
            add_constraints(expr, terms[i]);
        }
        debug("RQL:)\n");
#if GE_VERSION < PM_VERSION(2, 0, 0)
        BoolVarArgs terms_args(terms);
        bool_or(SELF, terms_args, var);
#else
        rel(SELF, BOT_OR, terms, var);
#endif
    }

    template <template <class> class Engine>
    static void run(RqlContext &pb, Search::Stop *stop) {
        double t0 = 0;
        int i = pb.solutions;
        Timer t;
        RqlSolver *s = new RqlSolver(pb);
        t.start();
        unsigned int n_p = 0;
        unsigned int n_b = 0;
        if (s->status() != SS_FAILED) {
#if GE_VERSION < PM_VERSION(3, 2, 0)
            n_p = s->propagators();
            n_b = s->branchings();
#else
#if GE_VERSION < PM_VERSION(5, 0, 0)
            n_p = s->propagators();
            n_b = s->branchers();
#else
            n_p = PropagatorGroup::all.size(*s);
            n_b = BrancherGroup::all.size(*s);
#endif
#endif
        }
#if GE_VERSION < PM_VERSION(2, 0, 0)
        Engine<RqlSolver> e(s);
#else
        Search::Options opts;
        // opts.c_d = pb.c_d;
        // opts.a_d = pb.a_d;
        opts.stop = stop;
        Engine<RqlSolver> e(s, opts);
#endif
        delete s;
        do {
            RqlSolver *ex = e.next();
            if (ex == NULL)
                break;

            ex->add_new_solution(pb);

            delete ex;
            t0 = t0 + t.stop();
        } while (--i != 0 && (pb.time < 0 || t0 < pb.time));
        Search::Statistics stat = e.statistics();
        if (pb.verbosity) {
            cout << endl;
            cout << "Initial" << endl
                 << "\tpropagators:   " << n_p << endl
                 << "\tbranchings:    " << n_b << endl
                 << endl
                 << "Summary" << endl
                 << "\truntime:       " << t.stop() << endl
                 << "\tsolutions:     "
                 << abs(static_cast<int>(pb.solutions) - i) << endl
                 << "\tpropagations:  " << stat.propagate << endl
                 << "\tfailures:      " << stat.fail << endl
#if GE_VERSION < PM_VERSION(3, 0, 0)
                 << "\tclones:        " << stat.clone << endl
                 << "\tcommits:       " << stat.commit << endl
#else
                 << "\tdepth:        " << stat.depth << endl
                 << "\tnode:       " << stat.node << endl
#endif
#if GE_VERSION < PM_VERSION(4, 2, 0)
                 << "\tpeak memory:   "
                 << static_cast<int>((stat.memory + 1023) / 1024) << " KB"
                 << endl
#endif
                ;
        }
    }

    /* We append each solutions to `sols` as a
   tuple `t` of the values assigned to each var
   that is t[i] = solution for var[i]
  */
    virtual void add_new_solution(RqlContext &pb) {
        PyObject *tuple, *ival;

        tuple = PyTuple_New(pb.nvars);

        for (int i = 0; i < pb.nvars; ++i) {
            ival = PyLong_FromLong(variables[i].val());
            PyTuple_SetItem(tuple, i, ival);
        }
        PyList_Append(pb.sols, tuple);
    }
    /* another function need by gecode kernel */
#if GE_VERSION < PM_VERSION(6,0,0)
    virtual Space *copy(bool share) { return new RqlSolver(share, *this); }
#else
    virtual Space *copy() { return new RqlSolver(*this); }
#endif
};

class FailTimeStop : public Search::Stop {
  private:
    Search::TimeStop *ts;
    Search::FailStop *fs;

  public:
    FailTimeStop(int fails, int time) : ts(0L), fs(0L) {
        if (time >= 0)
            ts = new Search::TimeStop(time);
        if (fails >= 0) {
            fs = new Search::FailStop(fails);
        }
    }
#if GE_VERSION < PM_VERSION(3, 1, 0)
    bool stop(const Search::Statistics &s) {
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
    bool stop(const Search::Statistics &s, const Search::Options &o) {
        int sigs = PyErr_CheckSignals();
        bool fs_stop = false;
        bool ts_stop = false;
        if (fs) {
            fs_stop = fs->stop(s, o);
        }
        if (ts) {
            ts_stop = ts->stop(s, o);
        }
        return sigs || fs_stop || ts_stop;
    }
#endif

    /// Create appropriate stop-object
    static Search::Stop *create(int fails, int time) {
        return new FailTimeStop(fails, time);
    }
};

static void _solve(RqlContext &ctx) {
    Search::Stop *stop = FailTimeStop::create(ctx.fails, ctx.time);

    RqlSolver::run<DFS>(ctx, stop);
}

static PyObject *rql_solve(PyObject *self, PyObject *args) {
    PyObject *sols = 0L;
    PyObject *constraints;
    PyObject *domains;
    long nvars, nvalues;
    if (!PyArg_ParseTuple(args, "OiO", &domains, &nvalues, &constraints))
        return NULL;
    sols = PyList_New(0);
    try {
        if (!PyList_Check(domains)) {
            throw RqlError();
        }
        nvars = PyList_Size(domains);
        RqlContext ctx(nvars, domains, nvalues, constraints, sols);
        _solve(ctx);
    } catch (RqlError &e) {
        Py_DECREF(sols);
        PyErr_SetString(PyExc_RuntimeError, "Error parsing constraints");
        return NULL;
    };
    return sols;
}

static PyMethodDef SolveRqlMethods[] = {
    {"solve", rql_solve, METH_VARARGS, "Solve RQL variable types problem."},
    {NULL, NULL, 0, NULL} /* Sentinel */
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {PyModuleDef_HEAD_INIT,
                                       "rql_solve",
                                       NULL,
                                       0,
                                       SolveRqlMethods,
                                       NULL,
                                       NULL,
                                       NULL,
                                       NULL};
#endif

PyMODINIT_FUNC
#if PY_MAJOR_VERSION >= 3
PyInit_rql_solve(void)
#else
initrql_solve(void)
#endif
{
    PyObject *m;
#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule("rql_solve", SolveRqlMethods);
#endif
    if (m == NULL)
#if PY_MAJOR_VERSION >= 3
        return NULL;
#else
        return;
#endif
#if PY_MAJOR_VERSION >= 3
    return m;
#endif
}
