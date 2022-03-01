"""Code for the inverse quantum fourier transform."""

import numpy as np

from qiskit import QuantumCircuit


def iqft(num_qubits):
    """
    Returns a gate that applies the inverse quantum fourier transform.

    Based on the implementation found in Qiskit's QPE tutorial:
    https://qiskit.org/textbook/ch-algorithms/quantum-phase-estimation.html
    """
    qc = QuantumCircuit(num_qubits)

    for qubit in range(num_qubits // 2):
        qc.swap(qubit, num_qubits - qubit - 1)

    for j in range(num_qubits):
        for m in range(j):
            qc.cp(-np.pi / float(2 ** (j - m)), m, j)
        qc.h(j)

    iqft_gate = qc.to_gate()
    iqft_gate.name = "IQFT"
    return iqft_gate
