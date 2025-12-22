from setuptools import setup

setup(
    name="quantum-subset-sum",
    version="0.1.0",
    description=("A quantum algorithm for solving the subset sum problem."),
    license="MIT",
    url="https://github.com/upsideon/quantum-subset-sum",
    packages=["qss"],
    requires=["numpy", "qiskit", "qiskit_aer", "qiskit_ibm_runtime"],
    install_requires=["numpy", "qiskit", "qiskit_aer", "qiskit_ibm_runtime"],
)
