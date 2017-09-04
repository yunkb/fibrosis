''' Bloch solver module   --   IMPERATIVE PARADIGMA
    Author:   David Nolte
    Email:    dnolte@dim.uchile.cl
    mod. on:  Feb 05, 2016
'''
from dolfin import *
import numpy as np

# TODO: init/assemble ONCE but repeat computations for different b-values?
#     i.e., just reset time t=0 and set initial condition.

# TODO: DRY RUN

# TODO: ITERATE OVER B VALUES .. inside class!!

# TODO: split assemble in "formulate_problem" and "assemble"????

# NOTE: THERE ARE TWO ASSEMBLY VERSIONS:
#           * assemble() -- function spaces, weak form, matrices
#           * formulate_problem() -- FS, weak form
#                   +
#             assemble_LS() -- matrices

# TODO: real advantage of OOP would be: define ABSTRACT SOLVER class and
#       INHERENT properties when defining problem specific class!!


def initialize(param, bval):
    ''' initialize '''
    from functions.inout import readmesh
    mesh, sd, bd = readmesh(param['io']['mesh'])

    # invoke solver
    sol, prec = param['num']['krylov']
    solver = KrylovSolver(sol, prec)

    # postproc / files
    if param['io']['vtk']:
        vtkfile = File(param['io']['results_dir'] + "/u_b" +
                       str(int(bval)).zfill(4) + ".pvd")
    if param['io']['timeseries']:
        Ulist = []
        tlist = []

    return mesh, sd, bd, solver, vtkfile, Ulist, tlist


def initial_condition():
    # Fenics Dxpression or Constant
    # set externally by Bloch.initial_condition(obj) = ...
    u0 = Constant((1.0, 0.0))
    return u0


# def formulate_problem(init, param, bval, mesh, sd):
#     ''' * Get/define physical properties
#         * Create FunctionSpaces
#         * Define weak formulation / linear and bilinear forms
#         -> pass on to assemble_LS()
#     '''
#     ui = None
#     a_M, a_N, a_K = None, None, None
#     if init:
#         # ~~~~~~~ Get physical properties ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#         # direction of diffusion sensitizing gradient
#         Gdir = param['phys']['pseq']['dir']
#         # get times of pulse sequence (delta, Delta for PGSE)
#         dtp = param['phys']['pseq']['dt']
#         # get diffusion coefficients of all subdomains
#         k = param['phys']['D']

#         # gyromagnetic ratio H1
#         pi = DOLFIN_PI
#         gm = 2*pi*42.57e3      # (Hz/mT)

#         # compute needed gradient strength to achieve set b-value
#         # assume Stejskal-Tanner PGSE rectangular pulses
#         #  NOTE: this depends on pulse sequence -> def function!
#         G = sqrt(bval/(gm**2*dtp[0]**2*(dtp[1]-dtp[0]/3.)))  # mT/mm

#         # Gradient matrix operator, independent of time and pulse design
#         Gr = Expression((('0', '-G*(x[0]*r0+x[1]*r1+x[2]*r2)'),
#                          ('G*(x[0]*r0+x[1]*r1+x[2]*r2)', '0')),
#                         G=G, r0=Gdir[0], r1=Gdir[1], r2=Gdir[2])

#         # ~~~~~~~~ V^2 Function space and Functions ~~~~~~~~~~~~~~~~~~~~~ #
#         V = FunctionSpace(mesh, "CG", param['num']['deg'])
#         W = V*V
#         dx = Measure('dx', domain=mesh, subdomain_data=sd)

#         u = TrialFunction(W)
#         v = TestFunction(W)

#         # ~~~~~~~~ Weak form ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#         a_M = inner(u, v)*dx
#         a_N = -gm*inner(dot(Gr, u), v)*dx
#         # diffusion: sum over all subdomains
#         # get subdomain indices
#         sdix = np.unique(sd.array())
#         a_K = inner(Constant(k[0])*grad(u), grad(v))*dx(int(sdix[0]))
#         for i in range(1, len(sdix)):
#             a_K += inner(Constant(k[i])*grad(u), grad(v))*dx(i)

#         # ~~~~~~~ Interpolate initial condition to function space ~~~~~~~ #
#         I = initial_condition()
#         ui = interpolate(I, W)

#     return ui, a_M, a_N, a_K


# def assemble_LS(init, param, t, ui, A0=None, M=None, N=None):
#     ''' Alternative to assemble().
#         Here, problem definition and assembly are SPLIT.
#         --> function formulate_problem()

#         NOTE: assume implicite backward step.
#         The forms a(u,v) and L(v) are time dependent. L via u1
#         (previous time step) and a(u,v) via f(t). Avoid repeated
#         assembly! f(t) changes 2x but is constant. a) Split time loop
#         into corresponding intervals. b) More general (arbitrary
#         sequences, e.g., oscillating): pre-assemble A and b.
#         (b) implemented!)
#         (http://fenicsproject.org/documentation/tutorial/timedep.html)
#         '''
#     dt = param['num']['dt']
#     dtp = param['phys']['pseq']['dt']
#     f = param['phys']['pseq']['f']
#     if init:
#         init = False
#         M = assemble(a_M)      # mass matrix
#         N = assemble(a_N)      # reaction term
#         K = assemble(a_K)           # diffusion

#         # NOTE: Combining these matrices defines the time stepper.
#         #       Generalize?
#         A0 = M + dt*K
#         N *= dt

#     A = A0 + f(t, dtp)*N
#     b = M*ui.vector()

#     # return ui so timestep doesn't need to define new function
#     return A, b, ui, init

def assemble(self, ui=None):
    # XXX: careful, there is a dolfin function with that name (I use!)
    ''' Assemble matrices
        If self.init is True (first run or externally set), redefine
            function spaces etc, reassemble matrices/vectors.
        Else, just assemble time dependent parts.
    '''
    param = self.param
    dtp = param['phys']['pseq']['dt']
    if self.init:
        self.init = False

        # Get physical properties.
        dt = param['num']['dt']
        self.f = param['phys']['pseq']['f']
        Gdir = param['phys']['pseq']['dir']
        k = param['phys']['D']

        pi = DOLFIN_PI
        gm = 2*pi*42.57e3      # (Hz/mT) gyromagnetic ratio H1
        # Stejskal-Tanner PGSE rectangular pulses
        G = sqrt(self.bval/(gm**2*dtp[0]**2*(dtp[1]-dtp[0]/3.)))  # mT/mm

        # Gradient matrix operator, time independent
        Gr = Expression((('0', '-G*(x[0]*r0+x[1]*r1+x[2]*r2)'),
                         ('G*(x[0]*r0+x[1]*r1+x[2]*r2)', '0')),
                        G=G, r0=Gdir[0], r1=Gdir[1], r2=Gdir[2])

        # Convert diffusion coefficients to UFL constants
        V = FunctionSpace(self.mesh, "CG", param['num']['deg'])
        W = V*V

        dx = Measure('dx', domain=self.mesh, subdomain_data=self.sd)

        # Initial condition
        I = self.initial_condition()
        ui = interpolate(I, W)       # TODO project??

        # BC: start with Neumann BC 0 on all boundaries (full reflective)
# ----------------- Formulate problem ------------------------------------- #
        # Define functions for variational form
        u = TrialFunction(W)
        v = TestFunction(W)

        # Implicite backward step
        # NOTE: The forms a(u,v) and L(v) are time dependent. L via u1
        # (previous time step) and a(u,v) via f(t). Avoid repeated
        # assembly! f(t) changes 2x but is constant. a) Split time loop
        # into corresponding intervals. b) More general (arbitrary
        # sequences, e.g., oscillating): pre-assemble A and b.
        # (b) implemented!)
        # (http://fenicsproject.org/documentation/tutorial/timedep.html)

        # Weak form
        a_M = inner(u, v)*dx
        a_N = -gm*inner(dot(Gr, u), v)*dx
        # diffusion: sum over all subdomains
        # get subdomain indices
        sdix = np.unique(self.sd.array())
        a_K = inner(Constant(k[0])*grad(u), grad(v))*dx(int(sdix[0]))
        for i in range(1, len(sdix)):
            a_K += inner(Constant(k[i])*grad(u), grad(v))*dx(i)

# ----------------- ASSEMBLE MATRICES ------------------------------------- #
        self.M = assemble(a_M)      # mass matrix
        self.N = assemble(a_N)      # reaction term
        K = assemble(a_K)           # diffusion

        # NOTE: Combining these matrices defines the time stepper.
        #       Generalize?
        self.A0 = self.M + dt*K
        self.N *= dt

    A = self.A0 + self.f(self.t, dtp)*self.N
    b = self.M*ui.vector()

    # return ui so timestep doesn't need to define new function
    return A, b, ui


def dirichlet(A, b, bc=None):
    return A, b


def timestep(init, t, solver, A, b, u):
    if not init:       # -> postproc output of initial condition
        solver.solve(A, u.vector(), b)
    return u


def postproc(param, u, t, T, vtkfile=None, bval=None, Ulist=None, tlist=None):
    io = param['io']
    U = None
    done = t >= T
    if MPI.rank(mpi_comm_world()) == 0 and not param['num']['dry']:
        if io['vtk']:
            vtkfile << u
        if io['timeseries']:
            # calculate U = integral(u)
            U = [assemble(u[0]*dx), assemble(u[1]*dx)]
            Ulist.append(U)
            tlist.append(t)

            if done:
                import h5py
                fname = "b"+str(int(bval)).zfill(4)+"_ts.h5"
                fdir = io['results']
                with h5py.File(fdir+"/"+fname, "w") as h5:
                    h5.create_dataset('time', data=tlist)
                    h5.create_dataset('U', data=Ulist)
                    h5.attrs['b'] = bval
                    h5.close()
        if io['signal_TE'] and done:
            # cumbersome integration:
            # R = FunctionSpace(self.mesh, "R", 0)
            # RR = R*R
            # c = TestFunction(RR)
            # S_TE = assemble(dot(u, c)*dx).array()
            # do something with S_TE... or separate function??

            # fast component-wise
            U = [assemble(u[0]*dx), assemble(u[1]*dx)]
    return U


# def assemble_all(init, param, t, ui, bval, mesh, sd):
#     if init:
#         ui, a_M, a_N, a_K = formulate_problem(init, param, bval, mesh, sd)
#         ui, A0, M, N, init = assemble_LS(init, param, t, ui, A0=None, M=None,
#                                          N=None)


def timeloop(param, bval, t, T):
    u = None
    mesh, sd, bd, solver, vtkfile, Ulist, tlist = initialize(param, bval)
    while t < T:
        # does NOTHING inf init == False. put into initialize !??
        A, b, u = assemble_LS(u)
        A, b = self.dirichlet(A, b)
        u = self.timestep(A, b, u)
        U = self.postproc(u, T)      # return integral of u (if applicable)
        print(self.t)
    return U

    # def dry_run(self):
    #     # init function spaces etc
    #     A, b, u = self.assemble(None)
    #     # NOTE: need to precompute assemble(ui[0]*dx), too?

    # def bval_iterate(self, T):
    #     ''' Iterate over all b-values, making use of initialization.
    #         NOTE: Does this really make sense? Part of assembly has to be
    #         repeated anyways, gain very little.
    #     '''
    #     Ub = []
    #     for bval in self.param['phys']['b']:
    #         self.bval = bval
    #         self.t = 0
    #         self.init = True
    #         tmp = self.timeloop(T)
    #         Ub.append(tmp)

    #     return Ub
