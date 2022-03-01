"""An implementation of a quantum algorithm for the subset sum problem."""

import numpy as np

from qiskit import ClassicalRegister, QuantumRegister, QuantumCircuit
from qiskit import Aer, assemble, transpile
from qiskit import IBMQ
from qiskit.assembler import disassemble
from qiskit.execute_function import execute
from qiskit.providers.ibmq.job import job_monitor

from .iqft import iqft


class QuantumSubsetSum:
    """
    A representation of an instance of the quantum subset sum problem.
    """

    def __init__(self, values, target_sum):
        """
        Creates a new instance of the quantum subset sum problem.

        Arguments:
            values: The set of values from which subsets will be drawn.
            target_sum: The target sum corresponding to solution subsets.

        Returns:
            QuantumSubsetSum
        """
        self.values = values
        self.target_sum = target_sum

        self.num_values = len(values)

        # The number of sum qubits is equal to the number necessary to store the
        # largest possible sum.
        self.num_sum_qubits = int(np.round(np.log(sum(values)) / np.log(2))) + 1

        # Given that we are using amplitude implication on subsets, we can guarantee that solution
        # states will have significantly high measurement probabilities after a number of iterations
        # equal to the square root of the number of subsets. In practice, it may be less, but this
        # number mitigates the worse case scenario.
        self.num_grover_iterations = int(np.sqrt(2 ** self.num_values))

        # An index qubit is created for each input value, including the target sum.
        num_indices = self.num_values + 1

        self.sums = QuantumRegister(self.num_sum_qubits)
        self.indices = QuantumRegister(num_indices)
        self.grover_output = QuantumRegister(1)
        self.indices_classical = ClassicalRegister(num_indices)

        self.qc = QuantumCircuit(
            self.sums, self.indices, self.grover_output, self.indices_classical
        )

        self.counts = {}

    def encode_phase(self, normalized_value, index, qc):
        """
        Encodes a value into the sum qubits and associates the value with an index qubit.

        Arguments:
            normalized_value: A value normalized so that it is between 0 and 1.
            index: The index qubit to associate the value with during phase encoding.
        """
        power = 1
        theta = 2 * np.pi * normalized_value
        for sum_qubit in range(self.sums.size):
            qc.cp(theta * power, self.sums[sum_qubit], self.indices[index])
            power *= 2

    def encode_values_in_phase(self, normalized_values, normalized_target):
        """
        Encodes input values and the negated target sum into the phase of the sum qubits
        via quantum phase estimation.

        Arguments:
            normalized_values: A set of values normalized to be between 0 and 1.
            normalized_target: The normalized target sum.

        Returns:
            qiskit.circuit.gate.Gate: The quantum phase estimation operation represented as a gate.
        """
        qc = QuantumCircuit(self.sums, self.indices)

        # Putting sum and index qubits into superposition.
        qc.h(self.sums)
        qc.h(self.indices)

        # Encoding set values.
        for index, value in enumerate(normalized_values):
            self.encode_phase(value, index, qc)

        # Encoding target sum as negative phase. This leads to it canceling out any subset
        # sums that are equal to the target sum, which we can take advantage of when carrying
        # out amplitude amplification.
        self.encode_phase(-normalized_target, len(normalized_values), qc)

        # Applying the inverse QFT to bring subet sums out of the frequency domain.
        qc.append(iqft(self.num_sum_qubits), self.sums)

        qpe_gate = qc.to_gate()
        qpe_gate.name = "QPE"
        return qpe_gate

    def oracle(self):
        """
        Marks states which represent subsets that add up to the target sum.

        Returns:
            qiskit.circuit.gate.Gate: The oracle operation represented as a gate.
        """
        qc = QuantumCircuit(self.sums, self.indices, self.grover_output)

        # If all the sum qubits are zero, we mark the state as a solution. We look for states
        # with zero sum due to the fact that we encoded the negative target sum. This makes
        # finding states significantly easier as the oracle does not change based on the target
        # sum.
        qc.x(self.sums)
        qc.mct(self.sums, self.grover_output)
        qc.x(self.sums)

        # Filtering out the all zero sums with all zero indices.
        qc.x(self.sums)
        qc.x(self.indices)
        qc.mct(self.sums[:] + self.indices[:], self.grover_output)
        qc.x(self.indices)
        qc.x(self.sums)

        oracle_gate = qc.to_gate()
        oracle_gate.name = "Oracle"
        return oracle_gate

    def diffuser(self, qpe_gate):
        """
        Amplifies the amplitudes of marked states while diminishing the amplitudes
        of unmarked states.

        Arguments:
            qpe_gate: The quantum phase estimation operation used to encode values.

        Returns:
            qiskit.circuit.gate.Gate: The diffuser operation represented as a gate.
        """
        qc = QuantumCircuit(self.sums, self.indices, self.grover_output)

        # Rolling back the quantum phase estimation operation used to encode values.
        qpe_inverse_gate = qpe_gate.inverse()
        qc.append(qpe_inverse_gate, self.sums[:] + self.indices[:])

        # Amplifying marked states and equivalently diminishing unmarked states.
        qc.x(self.sums)
        qc.x(self.indices)
        qc.mct(self.sums[:] + self.indices[:], self.grover_output)
        qc.x(self.indices)
        qc.x(self.sums)

        # Reapplying the quantum phase estimation operation used to encode values.
        qc.append(qpe_gate, self.sums[:] + self.indices[:])

        diffuser_gate = qc.to_gate()
        diffuser_gate.name = "Diffuser"
        return diffuser_gate

    def build(self):
        """
        Builds a quantum circuit that can solve a given instance of the subset sum problem.

        Returns:
            qiskit.QuantumCircuit: The quantum circuit for determining subset sum solutions.
        """

        # Putting Grover qubit into |->.
        self.qc.x(self.grover_output)
        self.qc.h(self.grover_output)

        # Normalizing values and target sum.
        normalized_values = normalize(self.values + [self.target_sum])
        normalized_target_sum = normalized_values[-1:][0]
        normalized_values = normalized_values[:-1]

        # Encoding values in phase of sum qubits resulting in a state which is a superposition
        # of all possible subset sums and their corresponding indices.
        qpe_gate = self.encode_values_in_phase(normalized_values, normalized_target_sum)
        self.qc.append(qpe_gate, self.sums[:] + self.indices[:])

        for _ in range(self.num_grover_iterations):
            # Executing an oracle which marks solution states.
            self.qc.append(
                self.oracle(), self.sums[:] + self.indices[:] + self.grover_output[:]
            )

            # Applying a diffuser operation specific to the quantum phase estimation
            # used to encode values.
            self.qc.append(
                self.diffuser(qpe_gate),
                self.sums[:] + self.indices[:] + self.grover_output[:],
            )

        # Measuring results.
        self.qc.measure(self.indices, self.indices_classical)

        return self.qc

    def simulate(self, qc):
        """
        Simulates a quantum circuit and returns measurements.

        Returns:
            dict: A set of measurements and their frequencies.
        """
        aer_sim = Aer.get_backend("aer_simulator")
        transpiled = transpile(qc, aer_sim)
        qobj = assemble(transpiled)
        result = aer_sim.run(qobj).result()
        counts = result.get_counts()
        self.counts = counts
        return counts

    def ibmq_execute(self, qc):
        """
        Executes a quantum circuit on an actual IBM quantum computer and returns measurements.

        Returns:
            dict: A set of measurements and their frequencies.
        """
        IBMQ.load_account()
        provider = IBMQ.get_provider(hub="ibm-q", group="open", project="main")
        backend = provider.get_backend("ibmq_bogota")

        transpiled = transpile(qc, backend)
        qobj = assemble(transpiled)
        circuits, _, _ = disassemble(qobj)
        job = execute(circuits, backend=backend, shots=10)
        job_monitor(job)

        result = job.result()
        counts = result.get_counts()
        self.counts = counts
        return counts

    def get_measurement_counts(self):
        """
        Returns the measurement counts associated with the most recent execution of the circuit.
        """
        return self.counts

    def process_measurements(self, counts):
        """
        Processes measurements to ensure we only return solutions with the highest probability.

        Returns:
            list((list, float)): A list of subsets representing solutions to the subset sum problem.
        """
        total_measurements = sum(list(counts.values()))
        counts = dict(sorted(counts.items(), key=lambda state: state[1], reverse=True))
        counts = list(counts.items())

        # Filtering out any of the subsets that were measured with low probability, but
        # are not solutions.
        answer_subsets = []
        for state, count in counts:
            # Lopping off the target sum qubit and reversing to process from the least
            # significant qubit first.
            subset_qubits = list(reversed(state[1:]))

            # If a qubit in the measurement state is set to 1, then the subset contains
            # the value at the corresponding index.
            subset = []
            for index, value in enumerate(subset_qubits):
                if value == "1":
                    subset.append(self.values[index])

            if sum(subset) == self.target_sum:
                # Returning the subset as well as its measurement probability.
                answer_subsets.append((subset, count / total_measurements))
            else:
                # We break out of the loop as soon as we hit a measurement which is not a solution.
                # This works as solutions have the highest measurement probability and hence will
                # come first in the sorted list.
                break

        return answer_subsets

    def execute(self, simulate=True):
        """
        Executes a quantum circuit that can solve the subset sum problem and returns results.
        """
        qc = self.build()

        counts = None
        if simulate:
            counts = self.simulate(qc)
        else:
            counts = self.ibmq_execute(qc)

        answer_subsets = self.process_measurements(counts)
        return answer_subsets


def normalize(values):
    """
    Normalizes the provided set of values.

    Arguments:
        values: The set of values to be normalized.

    Returns:
        numpy.ndarray: The set of values normalized between 0 and 1.
    """
    values = np.array(values)
    return values / values.sum()
