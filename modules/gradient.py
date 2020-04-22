import numpy as np
from modules.hamiltonian import Hamiltonian


class ProbabilityDerivative:
    """Perform measurements and calculates derivatives of probabilites for hamiltonian"""

    def __init__(self, hamiltonian: Hamiltonian, original_angles):
        self.hamiltonian = hamiltonian
        self.original_angles = original_angles
        self.n_spins = self.hamiltonian.n_spins

    def conjugated_angles(self):
        """
        Here we create new series of angles for gradient measurements. We use here the notation of bloch sphere basis.
        2 letters notation is exhaustively because basis choice is repeated for the following spines.
        For example "YZ" means "YZYZYZ...". Bloch notation means:
            - Z: theta=theta, phi=phi
            - X: theta=theta+pi/2, phi=phi
            - Y: thetha=pi/2, phi=phi+pi/2

        """
        original_angles = self.original_angles

        ZZ = np.copy(original_angles)
        XZ = np.copy(original_angles)
        YZ = np.copy(original_angles)
        ZX = np.copy(original_angles)
        ZY = np.copy(original_angles)
        for i in range(self.n_spins):
            if i % 2 == 0:
                XZ[i, 0] += np.pi / 2  # theta
                YZ[i, 0] = np.pi / 2  # theta
                YZ[i, 1] += np.pi / 2  # phi
            else:
                ZX[i, 0] += np.pi / 2  # theta
                ZY[i, 0] = np.pi / 2  # theta
                ZY[i, 1] += np.pi / 2  # phi
        return ZZ, XZ, YZ, ZX, ZY

    def measurements_for_gradient(self):
        """
        It's a key function of our work, where measurements are performed.
        we have 3 basis choices: B in {X, Y, Z}
        singles_B[i] returns [p(spin i is 0| measured in basis B), p(spin i is 1| measured in basis B)]
        corr_BC[i] returns [p(spin i is 0, spin (i+1) is 0 | spin i is measured in basis B, spin (i+1) is measured in basis C),
                                    p(01|BC),
                                    p(10|BC),
                                    p(11|BC)]
        """
        n_spins = self.n_spins
        hamiltonian = self.hamiltonian
        # Generate angles for measurements
        (angles_ZZ, angles_XZ, angles_YZ, angles_ZX, angles_ZY) = self.conjugated_angles()

        # Perform measurements
        measured_singles_ZZ, measured_corr_ZZ = hamiltonian.measure(angles_ZZ)
        measured_singles_XZ, measured_corr_XZ = hamiltonian.measure(angles_XZ)
        measured_singles_YZ, measured_corr_YZ = hamiltonian.measure(angles_YZ)
        measured_singles_ZX, measured_corr_ZX = hamiltonian.measure(angles_ZX)
        measured_singles_ZY, measured_corr_ZY = hamiltonian.measure(angles_ZY)

        # In Z basis we immediately got answers, so just for consistency:
        singles_Z = measured_singles_ZZ
        corr_ZZ = measured_corr_ZZ

        # Create blanks for other singles and corr
        singles_X = np.zeros((n_spins, 2))
        singles_Y = np.zeros((n_spins, 2))
        corr_XZ = np.zeros((n_spins - 1, 4))
        corr_YZ = np.zeros((n_spins - 1, 4))
        corr_ZX = np.zeros((n_spins - 1, 4))
        corr_ZY = np.zeros((n_spins - 1, 4))

        for i in range(n_spins):

            if i % 2 == 0:
                singles_X[i] = measured_singles_XZ[i]
                singles_Y[i] = measured_singles_YZ[i]
                if i != n_spins - 1:  # not last spin
                    corr_ZX[i] = measured_corr_ZX[i]
                    corr_ZY[i] = measured_corr_ZY[i]
                    corr_XZ[i] = measured_corr_XZ[i]
                    corr_YZ[i] = measured_corr_YZ[i]

            else:
                singles_X[i] = measured_singles_ZX[i]
                singles_Y[i] = measured_singles_ZY[i]
                if i != n_spins - 1:
                    corr_ZX[i] = measured_corr_XZ[i]
                    corr_ZY[i] = measured_corr_YZ[i]
                    corr_XZ[i] = measured_corr_ZX[i]
                    corr_YZ[i] = measured_corr_ZY[i]


        self.singles_Z = singles_Z
        self.singles_X = singles_X
        self.singles_Y = singles_Y

        self.corr_ZZ = corr_ZZ
        self.corr_XZ = corr_XZ
        self.corr_YZ = corr_YZ
        self.corr_ZX = corr_ZX
        self.corr_ZY = corr_ZY

        # print(self.corr_ZZ)

    def d_prob(self, pZ, pX, pY):
        """By given probabilities of measurements in Z, X and Y basis
        returns vector of derivatives for each spin of shape (n_spins, 2)"""

        # !! Returns 0 if get 1/2 !!
        theta = self.original_angles[:, 0]  # we need only thetas
        print(theta)

        # Probabilities of getting 0 in each basis (singles)

        # Auxiliary vectors
        V1 = pZ - (1 / 2)
        V2 = pX - (1 / 2)

        # Auxilary coefficients for probabilities computation
        A = - np.cos(theta) * V1 + np.sin(theta) * V2
        B = np.sin(theta) * V1 + np.cos(theta) * V2
        C = pY - (1 / 2)
        print(f"A = {A}")
        print(f"B = {B}")
        print(f"C = {C}")
        print("")

        # Actually, this is derivatives of probabilities by d_theta and d_phi
        d_theta = A * np.sin(theta) + B * np.cos(theta)  # \frac{d_prob}{d_theta}
        d_phi = C * np.sin(theta)  # \frac{d_prob}{d_phi}

        d_prob = np.array([d_theta, d_phi]).T  # shape (n_spins, 2)
        return d_prob

    def singles_grad_construct(self):
        """With measured singles returns differentials of probabilities"""

        singles_d_prob = np.zeros((2, self.n_spins, 2))  # shape (states, n_spins, 2angles)

        # Run over all states: p(0) and p(1).   TODO: optimize it, because p(1) = 1 - p(0)
        for state in range(2):
            pZ = self.singles_Z[:, state]  # shape (n_spins, 1)
            pX = self.singles_X[:, state]
            pY = self.singles_Y[:, state]

            singles_d_prob[state] += self.d_prob(pZ, pX, pY)  # shape (states, n_spins, 2angles)


        # For futher interest we need to spap axes
        singles_d_prob = np.swapaxes(singles_d_prob, 0, 1)  # so now shape = (n_spins, states, angle)

        return singles_d_prob

    def corr_grad_construct(self):
        """
        we use here the following labels for states:
        00 -> 0
        01 -> 1
        10 -> 2
        11 -> 3
        """
        left_corr_d_prob = np.zeros((4, self.n_spins, 2))  # (states, n_spins, 2angles)
        right_corr_d_prob = np.zeros((4, self.n_spins, 2))  # (states, n_spins, 2angles)

        tail = np.array([0.5])  #we will add it to keep dimensions

        for state in range(4):
            # Responsible for derivative by left spin

            pZZ = self.corr_ZZ[:, state]
            pXZ = self.corr_XZ[:, state]
            pYZ = self.corr_YZ[:, state]

            pZZ = np.concatenate((pZZ, tail), axis=0)
            pXZ = np.concatenate((pXZ, tail), axis=0)
            pYZ = np.concatenate((pYZ, tail), axis=0)

            left_corr_d_prob[state] += self.d_prob(pZZ, pXZ, pYZ)
            # print(left_corr_d_prob[state])

            # Responsible for derivative by right spin
            pZZ = self.corr_ZZ[:, state]
            pZX = self.corr_ZX[:, state]
            pZY = self.corr_ZY[:, state]
            # print(pZX)

            pZZ = np.concatenate((tail, pZZ), axis=0)
            pZX = np.concatenate((tail, pZX), axis=0)
            pZY = np.concatenate((tail, pZY), axis=0)

            right_corr_d_prob[state] += self.d_prob(pZZ, pZX, pZY)
            # print(right_corr_d_prob[state])
        # print('')
        left_corr_d_prob = np.swapaxes(left_corr_d_prob, 0, 1)  # so now shape = (n_spins, states, angle)
        right_corr_d_prob = np.swapaxes(right_corr_d_prob, 0, 1)  # so now shape = (n_spins, states, angle)
        # print(left_corr_d_prob[:, :, 0] + right_corr_d_prob[:, :, 0])
        return left_corr_d_prob, right_corr_d_prob


class Gradient:
    def __init__(self, hamiltonian_t: Hamiltonian, hamiltonian_g, original_angles):
        self.hamiltonian_t = hamiltonian_t
        self.hamiltonian_g = hamiltonian_g
        self.original_angles = original_angles

        # Initiate object of class ProbabilityDerivative for computation derivatives
        self.prob_der_t = ProbabilityDerivative(hamiltonian_t, original_angles)
        self.prob_der_g = ProbabilityDerivative(hamiltonian_g, original_angles)

    def loss_gradient(self):
        """calculates gradient vector"""
        loss_grad = 0
        s_loss_grad = 0
        c_loss_grad = 0
        self.prob_der_t.measurements_for_gradient()
        self.prob_der_g.measurements_for_gradient()

        # ## Handle with singles:
        # # Construct gradients of shape (n_spins, states, angles)
        # singles_grad_t = self.prob_der_t.singles_grad_construct()
        # singles_grad_g = self.prob_der_g.singles_grad_construct()
        #
        # # We should add dimension , because singles have shapes (n_spins, states)
        # singles_prob_t = np.expand_dims(self.prob_der_t.singles_Z, axis=2)
        # singles_prob_g = np.expand_dims(self.prob_der_g.singles_Z, axis=2)
        #
        # # Sum over axis 1 (states) is resulting gradient
        # s_loss_grad += np.sum(2 * (singles_prob_t - singles_prob_g) * \
        #                  (singles_grad_t - singles_grad_g), axis=1)

        ## Handle with correlators
        tail = np.zeros((1, 4, 1))

        # Construct gradients of shape (n_spins, states, angles)
        left_corr_grad_t, right_corr_grad_t = self.prob_der_t.corr_grad_construct()
        left_corr_grad_g, right_corr_grad_g = self.prob_der_g.corr_grad_construct()

        # We should add dimension , because corrs have shapes (n_spins, states)
        corr_prob_t = np.expand_dims(self.prob_der_t.corr_ZZ, axis=2)
        corr_prob_g = np.expand_dims(self.prob_der_g.corr_ZZ, axis=2)  # now (n_spins, states, 2angles)


        # For left spins in correlators

        left_corr_prob_t = np.concatenate((corr_prob_t, tail), axis=0)
        left_corr_prob_g = np.concatenate((corr_prob_g, tail), axis=0)

        # Sum over axis 1 (states) is resulting gradient
        c_loss_grad += \
            np.sum(2 * (left_corr_prob_t - left_corr_prob_g) * (left_corr_grad_t - left_corr_grad_g), axis=1)

        # For right spins in correlators

        right_corr_prob_t = np.concatenate((tail, corr_prob_t), axis=0)
        right_corr_prob_g = np.concatenate((tail, corr_prob_g), axis=0)

        c_loss_grad += \
            np.sum(2 * (right_corr_prob_t - right_corr_prob_g) * (right_corr_grad_t - right_corr_grad_g), axis=1)



        loss_grad = c_loss_grad + s_loss_grad
        # print(np.linalg.norm(s_loss_grad) / (np.linalg.norm(s_loss_grad) + np.linalg.norm(c_loss_grad)))
        self.loss_grad = s_loss_grad
        # print(s_loss_grad)
        return loss_grad

    def gradient_descent(self, lr=0.01, num_iterations=10):
        """Perform gradient descent"""
        for i in range(num_iterations):
            grad = self.loss_gradient()
            self.original_angles += lr * grad

        return self.original_angles


