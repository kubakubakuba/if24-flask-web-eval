from qtrvsim import QtRVSim

sim = QtRVSim(args="--d-regs --dump-cycles --cycle-limit 1000", submission_file="file.S")

ending_regs = {
	"a1": 2,
	"a2": 4,
	"a3": 6,
}

starting_mem = {
	"array_start": [2, 4],
}

ending_mem = {
	"array_start": [2, 4, 6],
}

sim.set_reference_ending_regs(ending_regs)

sim.set_starting_memory(starting_mem)

sim.set_reference_ending_memory(ending_mem)

#sim.set_private() #optional, if set to true, does not show errors

sim.run("Testcase 1")

print(sim.get_log())
print(sim.get_scores()["cycles"] if sim.get_result() == 0 else "-1")

sim.reset()