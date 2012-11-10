""" Scalar.py: Implements HMMs with discrete observations.
Copyright (c) 2003, 2007, 2008, 2012 Andrew M. Fraser

"""

import random, numpy
def print_V(V):
    for x in V:
        print('%-6.3f'%x,end='')
    print('|')
def print_Name_V(name,V):
    print(name+' =',end='')
    print_V(V)
def print_Name_VV(name,VV):
    print('  '+name+' =')
    for V in VV:
        print('   ',end='')
        print_V(V)

## ----------------------------------------------------------------------
class HMM:
    """A Hidden Markov Model implementation with the following
    groups of methods:

    Tools for applications: forward(), backward(), train(), decode(),
    reestimate() and simulate()

    Test the code in this file by manipulating the HMM in Figure 1.6
    (fig:dhmm) in the book.

    >>> P_S0 = numpy.array([1./3., 1./3., 1./3.])
    >>> P_S0_ergodic = numpy.array([1./7., 4./7., 2./7.])
    >>> P_ScS = numpy.array([
    ...         [0,   1,   0],
    ...         [0,  .5,  .5],
    ...         [.5, .5,   0]
    ...         ],numpy.float64)
    >>> P_YcS = numpy.array([
    ...         [1, 0,     0],
    ...         [0, 1./3., 2./3.],
    ...         [0, 2./3., 1./3.]
    ...         ])
    >>> mod = HMM(P_S0,P_S0_ergodic,P_ScS,P_YcS)
    >>> S,Y = mod.simulate(500)
    >>> Y = numpy.array(Y,numpy.int32)
    >>> E = mod.decode(Y)
    >>> table = ['%3s, %3s, %3s'%('y','S','Decoded')]
    >>> table += ['%3d, %3d, %3d'%triple for triple in zip(Y,S,E[:10])]
    >>> for triple in table:
    ...     print(triple)
      y,   S, Decoded
      2,   1,   1
      2,   1,   1
      1,   2,   2
      0,   0,   0
      1,   1,   1
      1,   2,   2
      2,   1,   1
      1,   2,   2
      2,   1,   1
      2,   2,   1
    >>> L = mod.train(Y,N_iter=4)
    it= 0 LLps=  -0.920
    it= 1 LLps=  -0.918
    it= 2 LLps=  -0.918
    it= 3 LLps=  -0.917
    >>> mod.dump()
    dumping a <class '__main__.HMM'> with 3 states
     P_S0         =0.000 0.963 0.037 |
     P_S0_ergodic =0.142 0.580 0.278 |
      P_ScS =
       0.000 1.000 0.000 |
       0.000 0.519 0.481 |
       0.512 0.488 0.000 |
      P_YcS =
       1.000 0.000 0.000 |
       0.000 0.335 0.665 |
       0.000 0.726 0.274 |
    """
    def __init__(
        self,         # HMM instance
        P_S0,         # Initial distribution of states
        P_S0_ergodic, # Stationary distribution of states
        P_ScS,        # Transition probabilities: State Conditioned on State
        P_YcS         # Observation probabilities: Y Condidtioned on State
        ):
        """Builds a new Hidden Markov Model"""
        self.N =len(P_S0)
        self.P_S0 = numpy.matrix(P_S0)
        self.P_S0_ergodic = numpy.matrix(P_S0_ergodic)
        self.P_ScS = numpy.matrix(P_ScS)
        self.P_YcS = numpy.array(P_YcS)
        self.Py = None
        self.alpha = None
        self.gamma = None
        self.beta = None
        return # End of __init__()
    def Py_calc(
        self,    # HMM
        y        # A sequence of integer observations
        ):
        """
        Allocate self.Py and assign values self.Py[t,i] = P(y(t)|s(t)=i)
        """

        # Check size and initialize self.Py
        self.T = len(y)
        if self.Py == None or self.Py.shape != (self.T,self.N):
            self.Py = numpy.zeros((self.T,self.N),numpy.float64)
        for t in range(self.T):
            self.Py[t,:] = self.P_YcS[:,y[t]]
        return self.Py # End of Py_calc()
    def forward(self):
       """
       On entry:
       self       is an HMM
       self.Py    has been calculated
       self.T     is length of Y
       self.N     is number of states
       On return:
       self.gamma[t] = Pr{y(t)=y(t)|y_0^{t-1}}
       self.alpha[t,i] = Pr{s(t)=i|y_0^t}
       return value is log likelihood of all data
       """

       # Ensure allocation and size of alpha and gamma
       if self.alpha == None or self.alpha.shape != (self.T,self.N):
           self.alpha = numpy.zeros((self.T,self.N),numpy.float64)
       if self.gamma == None or len(self.gamma) != self.T:
           self.gamma = numpy.zeros((self.T,),numpy.float64)
       last = numpy.matrix(self.P_S0) # Copy
       lastA = last.A # View as array to make * element-wise multiplicaiton
       for t in range(self.T):
           lastA *= self.Py[t]              # Element-wise multiply
           self.gamma[t] = lastA.sum()
           lastA /= self.gamma[t]
           self.alpha[t,:] = lastA[0,:]
           last[:,:] = last*self.P_ScS      # Vector matrix product in place
       return (numpy.log(self.gamma)).sum() # End of forward()
    def backward(self):
        """
        On entry:
        self    is an HMM
        y       is a sequence of observations
        exp(PyGhist[t]) = Pr{y(t)=y(t)|y_0^{t-1}}
        On return:
        for each state i, beta[t,i] = Pr{y_{t+1}^T|s(t)=i}/Pr{y_{t+1}^T}
        """
        # Ensure allocation and size of beta
        if self.beta == None or self.beta.shape != (self.T,self.N):
            self.beta = numpy.zeros((self.T,self.N),numpy.float64)
        lastbeta = numpy.mat(numpy.ones(self.beta.shape[1]))
        lastbetaA = lastbeta.A[0,:]   # Array view so * is element-wise multiply
        pscst = self.P_ScS.T               # Transpose view
        # iterate
        for t in range(self.T-1,-1,-1):
            self.beta[t,:] = lastbetaA
            lastbeta[:,:] = (lastbetaA*self.Py[t,:]/self.gamma[t])*pscst
        return # End of backward()
    def train(self, y, N_iter=1, display=True):
        # Do (N_iter) BaumWelch iterations
        LLL = []
        for it in range(N_iter):
            self.Py_calc(y)
            LLps = self.forward()/len(y)
            if display:
                print("it= %d LLps= %7.3f"%(it,LLps))
            LLL.append(LLps)
            self.backward()
            self.reestimate(y)
        return LLL # End of train()
    def reestimate_s(self):
        """ Reestimate state transition probabilities and initial
        state probabilities.  Given the observation probabilities, ie,
        self.state[s].Py[t], given alpha, beta, gamma, and Py, these
        calcuations are independent of the observation model
        calculations."""
        u_sum = numpy.zeros((self.N,self.N),numpy.float64)
        new_P_S0 = numpy.zeros((self.N,))
        new_P_S0_ergodic = numpy.zeros((self.N,))
        for t in range(self.T-1):
            u_sum += numpy.outer(self.alpha[t]/self.gamma[t+1],
                                 self.Py[t+1]*self.beta[t+1,:])
        self.alpha *= self.beta
        new_P_S0_ergodic += self.alpha.sum(axis=0)
        new_P_S0 += self.alpha[0]
        assert u_sum.shape == self.P_ScS.shape
        ScST = self.P_ScS.A.T # To get element wise multiplication and correct /
        ScST *= u_sum.T
        ScST /= ScST.sum(axis=0)
        self.P_S0 = numpy.mat(new_P_S0/new_P_S0.sum())
        self.P_S0_ergodic = numpy.mat(new_P_S0_ergodic/new_P_S0_ergodic.sum())
        return (self.alpha,new_P_S0_ergodic) # End of reestimate_s()
    def reestimate(self,y):
        """ Reestimate all paramters.  In particular, reestimate observation
        model.
        """
        w,sum_w = self.reestimate_s()
        if not type(y) == numpy.ndarray:
            y = numpy.array(y,numpy.int32)
        assert(y.dtype == numpy.int32 and y.shape == (self.T,))
        for yi in range(self.P_YcS.shape[1]):
            self.P_YcS[:,yi] = w.take(numpy.where(y==yi)[0],axis=0
                                      ).sum(axis=0)/sum_w
        return # End of reestimate()
    def decode(self,y):
        """Use the Viterbi algorithm to find the most likely state
           sequence for a given observation sequence y"""
        self.Py_calc(y)
        pred = numpy.zeros((self.T, self.N), numpy.int32) # Best predecessors
        ss = numpy.zeros((self.T, 1), numpy.int32)        # State sequence
        L_S0, L_ScS, L_Py = (numpy.log(numpy.maximum(x,1e-30)) for x in
                             (self.P_S0,self.P_ScS,self.Py))
        nu = L_Py[0] + L_S0
        for t in range(1,self.T):
            omega = L_ScS.T + nu
            pred[t,:] = omega.T.argmax(axis=0)   # Best predecessor
            nu = pred[t,:].choose(omega.T) + L_Py[t]
        lasts = numpy.argmax(nu)
        for t in range(self.T-1,-1,-1):
            ss[t] = lasts
            lasts = pred[t,lasts]
        return ss.flat # End of viterbi
    # End of decode()
    def simulate(self,length,seed=3):
        """generates a random sequence of observations of given length"""
        random.seed(seed)
        # Set up cumulative distributions
        cum_init = numpy.cumsum(self.P_S0_ergodic.A[0])
        cum_tran = numpy.cumsum(self.P_ScS.A,axis=1)
        cum_y = numpy.cumsum(self.P_YcS,axis=1)
        # Initialize lists
        outs = []
        states = []
        def cum_rand(cum): # A little service function
            return numpy.searchsorted(cum,random.random())
        # Select initial state
        i = cum_rand(cum_init)
        # Select subsequent states and call model to generate observations
        for t in range(length):
            states.append(i)
            outs.append(cum_rand(cum_y[i]))
            i = cum_rand(cum_tran[i])
        return (states,outs) # End of simulate()
    def link(self, From, To, P):
        """ Create (or remove) a link between state "From" and state "To".
        The strength of the link is a function of both the argument
        "P" and the existing P_ScS array.  Set P_ScS itself if you
        need to set exact values.  Use this method to modify topology
        before training.

        FixMe: No test coverage.
        """
        self.P_ScS[From,To] = P
        self.P_ScS[From,:] /= self.P_ScS[From,:].sum()
    def dump_base(self):
        print("dumping a %s with %d states"%(self.__class__,self.N))
        print_Name_V(' P_S0        ',self.P_S0.A[0])
        print_Name_V(' P_S0_ergodic',self.P_S0_ergodic.A[0])
        print_Name_VV('P_ScS', self.P_ScS.A)
        return #end of dump_base()
    def dump(self):
        self.dump_base()
        print_Name_VV('P_YcS', self.P_YcS)
        return #end of dump()
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

#--------------------------------
# Local Variables:
# mode: python
# End:
