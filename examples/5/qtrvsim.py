import subprocess
from datetime import datetime
import re
from collections import defaultdict
import os

class QtRVSim:
	def __init__(self, args="", submission_file="", working_dir=""):
		'''Initialize the evaluator with the submission file, arguments, and registers and memory to compare.'''

		self.log = f"Evaluation started on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
		self.log += f"Arguments: {args}\n"
		#self.log += f"Submission file: {submission_file}\n\n"
		self.log += f"Error log:"

		self.working_dir = working_dir

		self.args = args
		self.mem_arg = ""
		self.dump_mem_arg = ""
		self.uart_arg = ""
		self.uart_file = ""
		self.custom_files = []
		self.submission_file = submission_file

		self.compare_registes = defaultdict(str) # list of registers to compare
		self.reference_memory = defaultdict(list) # list of memory to compare
		self.reference_uart = ""
		self.input_uart = ""
		self.starting_memory_addresses = []

		self.reference_ending_memory_addr = 0
		self.reference_ending_memory_length = 0

		self.do_compare_registers = False
		self.do_compare_memory = False
		self.do_set_starting_memory = False
		self.do_set_compare_uart = False
		self.do_set_input_uart = False

		self.cycles = -1
		self.result = -1
		self.is_private = False
		self.cache_stats = defaultdict(int)
		self.scores = defaultdict(int)

		self.timeout_time = 10 #seconds

		self.regs = defaultdict(int)
		self.mem = defaultdict(list)
		self.uart = ""

		self.verbose = False

		self.mem_output_files_prefix = working_dir + "/"
		self.starting_memory_files_prefix = working_dir + "/"

		self.mem_output_files = []
		self.starting_memory_files = []

		self.register_names = [
			"zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
			"s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
			"a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
			"s8", "s9", "s10","s11", "t3", "t4", "t5", "t6"
		]

		self.results = {}

		self.makefile_present = False
		self.makefile_successfull = True
		self.makefile_log = ""
	
	def get_result(self):
		'''Return the result of the evaluation.'''
		return self.result
	
	def get_cycles(self):
		'''Return the cycles of the evaluation.'''
		return self.cycles
	
	def get_scores(self):
		'''Return the scores of the evaluation.'''
		return self.scores
	
	def get_log(self):
		'''Return the log of the evaluation.'''
		return self.log
	
	def set_args(self, args):
		'''Set the arguments to pass to qtrvsim.'''
		self.args = args

	def set_submission_file(self, submission_file):
		'''Set the submission file to evaluate.'''
		self.submission_file = submission_file

	def set_do_compare_registers(self, val=True):
		'''Set whether to compare registers or not.'''
		self.do_compare_registers = val

	def set_do_compare_memory(self, val=True):
		'''Set whether to compare memory or not.'''
		self.do_compare_memory = val
		if not val:
			self.mem_arg = ""
			self.dump_mem_arg = ""

	def set_do_compare_uart(self, val=True):
		'''Set whether to compare uart or not.'''
		self.do_set_compare_uart = val

	def set_reference_ending_regs(self, reg_dict):
		'''Pass a dict of values to compare against.'''
		self.set_do_compare_registers(True) #compare registers
		self.compare_registes = reg_dict

	def set_reference_ending_uart(self, uart, uart_file):
		'''Set the reference uart output.'''
		self.set_do_compare_uart(True) #compare uart
		self.reference_uart = uart
		self.uart_file = f"{self.working_dir}/{uart_file}"
		self.uart_arg += f" --serout {self.uart_file}"

	def set_starting_memory(self, mem):
		'''Set the starting memory. Pass an array of pairs (address, value).'''

		for address in mem.keys():
			self.starting_memory_addresses.append(address)
			curr_starting_memory_file = f"{self.starting_memory_files_prefix}{address}.in"
			self.starting_memory_files.append(curr_starting_memory_file)

			with open(curr_starting_memory_file, 'w') as file:
				for val in mem[address]:
					file.write(f"{val}\n")

			self.mem_arg += f" --load-range {address},{curr_starting_memory_file}"

	def set_reference_ending_memory(self, mem):
		'''Pass an array of pairs (address, value) to compare against.'''
		self.set_do_compare_memory(True) #compare memory

		for address in mem.keys():
			curr_mem_output_file = f"{self.mem_output_files_prefix}{address}.out"

			self.mem_output_files.append(curr_mem_output_file)
			memory_len = len(mem[address])

			self.mem_arg += f" --dump-range {address},{memory_len*4},{curr_mem_output_file}"
			for val in mem[address]:
				self.reference_memory[address].append(val)

	def rgx_get_cycles(self, log):
		'''Get the number of cycles from the stdout of qtrvsim.'''
		match = re.search(r"^cycles: (\d+)$", log, re.MULTILINE)
		if match is not None:
			self.cycles = int(match.group(1))
		else:
			self.cycles = -1

	def read_mem_output_file(self):
		'''Read the memory file and set the self.mem dictionary.'''
		self.mem = defaultdict(list) #clear the memory

		for address in self.reference_memory.keys():
			curr_mem_output_file = f"{self.mem_output_files_prefix}{address}.out"
			with open(curr_mem_output_file, 'r') as file:
				for line in file:
					mem_val = line.strip()
					self.mem[address].append(int(mem_val, 16))

	def read_uart_file(self):
		'''Read the uart file and set the self.uart dictionary.'''
		self.uart = ""
		with open(f"{self.mem_output_files_prefix}__uart.out", 'r') as file:
			self.uart = file.read()

	def set_input_uart(self, uart, uart_file):
		'''Save the uart file.'''
		self.input_uart = f"{self.working_dir}/{uart_file}"
		with open(f"{self.input_uart}", 'w') as file:
			file.write(uart)
		self.uart_arg += f" --serin {self.input_uart}"

	def string_diff_and_hex(self, original: str, comparison: str):
		bytes1 = bytes(original, 'utf-8')
		bytes2 = bytes(comparison, 'utf-8')
		log = []

		for i in range(max(len(bytes1), len(bytes2))):
			byte1 = bytes1[i] if i < len(bytes1) else None
			byte2 = bytes2[i] if i < len(bytes2) else None

			if byte1 != byte2:
				byte1_hex = f'{byte1:02x}' if byte1 is not None else 'None'
				byte2_hex = f'{byte2:02x}' if byte2 is not None else 'None'
				log.append(f"position {i}: expected {byte1_hex}, got {byte2_hex}")

		return '\n'.join(log)

	def clear_files(self):
		'''Clear the memory and starting memory files.'''
		for file in self.mem_output_files + self.starting_memory_files + [self.uart_file] + [self.input_uart] + self.custom_files:
			try:
				os.remove(file)
			except:
				pass

	def end_eval(self, testcase):
		self.log += f"\n\nEvaluation ended on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
		print(self.results)
		score = self.results[testcase][1] if self.results[testcase][0] == 0 else -1
		self.log += f"Result: {score}\n"
		self.clear_files()

	def set_private(self):
		'''Set the evaluation to private.'''
		self.is_private = True

	def create_file(self, file_name, content):
		'''Create a file in the working directory.'''
		with open(f"{self.working_dir}/{file_name}", 'w') as file:
			file.write(content)

		self.custom_files.append(f"{self.working_dir}/{file_name}")

	def reset(self):
		self.do_compare_memory = False
		self.do_compare_registers = False
		self.is_private = False
		self.starting_memory_addr = 0
		self.reference_ending_memory_addr = 0
		self.reference_ending_memory_length = 0
		self.mem = defaultdict(list)
		self.regs = defaultdict(int)
		self.compare_registes = defaultdict(int)
		self.reference_memory = defaultdict(list)

	def rgx_get_cache_stats(self, log):
		'''Get the cache stats from the stdout of qtrvsim. Set them to the self.cache_stats dictionary.'''

		patterns = {
			r"^i-cache:reads: (\d+)$": ("i-cache:reads", int),
			r"^i-cache:hit: (\d+)$": ("i-cache:hit", int),
			r"^i-cache:miss: (\d+)$": ("i-cache:miss", int),
			r"^i-cache:hit-rate: (\d+\.\d+)$": ("i-cache:hit-rate", float),
			r"^i-cache:stalled-cycles: (\d+)$": ("i-cache:stalled-cycles", int),
			r"^i-cache:improved-speed: (\d+\.\d+)$": ("i-cache:improved-speed", float),
			r"^d-cache:reads: (\d+)$": ("d-cache:reads", int),
			r"^d-cache:hit: (\d+)$": ("d-cache:hit", int),
			r"^d-cache:miss: (\d+)$": ("d-cache:miss", int),
			r"^d-cache:hit-rate: (\d+\.\d+)$": ("d-cache:hit-rate", float),
			r"^d-cache:stalled-cycles: (\d+)$": ("d-cache:stalled-cycles", int),
			r"^d-cache:improved-speed: (\d+\.\d+)$": ("d-cache:improved-speed", float),
		}

		for pattern, (stat_key, value_type) in patterns.items():
			match = re.search(pattern, log, re.MULTILINE)
			if match:
				self.cache_stats[stat_key] = value_type(match.group(1))
		
	def rgx_get_registers(self, log):
		'''Get the registers from the stdout of qtrvsim. Set them to the self.regs dictionary.'''
		self.regs = defaultdict(int) #clear the registers

		# Patterns for registers
		patterns = {
			r"PC:(0x[0-9a-fA-F]+)": "PC",
			**{rf"R{i}:(0x[0-9a-fA-F]+)": f"R{i}" for i in range(32)},
			r"mvendorid: (0x[0-9a-fA-F]+)": "mvendorid",
			r"marchid: (0x[0-9a-fA-F]+)": "marchid",
			r"mimpid: (0x[0-9a-fA-F]+)": "mimpid",
			r"mhardid: (0x[0-9a-fA-F]+)": "mhardid",
			r"mstatus: (0x[0-9a-fA-F]+)": "mstatus",
		}

		for pattern, reg_key in patterns.items():
			match = re.search(pattern, log, re.MULTILINE)
			if match:
				self.regs[reg_key] = int(match.group(1), 16)
		
		for i in range(32):
			if f"R{i}" in self.regs:
				self.regs[self.register_names[i]] = self.regs.pop(f"R{i}") #replace Ri values with the register names

	def set_verbose(self, val=True):
		'''Set whether to print the stdout and stderr of qtrvsim to the console.'''
		self.verbose = val

	def log_test_name(self, test_name):
		'''Log the name of the test.'''
		
		self.log += f"\nRunning: '{test_name}'\n"

	def log_test_result(self, test_name):
		'''Log the name of the test.'''
		failed = self.result != 0

		if failed:
			self.log += f"\n{test_name} - FAILED\n"
		else:
			self.log += f"\n{test_name} - PASSED\n"

	def create_makefile(self, makefile):
		'''Create a makefile in the working directory.'''
		self.makefile_present = True
		with open(self.mem_output_files_prefix + "Makefile", 'w') as f:
			f.write(makefile)

	def run_make(self):
		'''Run make in the working directory.'''
		command = ["make"]
		try:
			process = subprocess.Popen(command, cwd=self.mem_output_files_prefix, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdout, stderr = process.communicate(timeout=self.timeout_time)
		except subprocess.TimeoutExpired:
			process.kill()
			stdout, stderr = None, None
			self.log += f"\nKilled after {self.timeout_time} seconds, while running make."
			self.makefile_successfull = False
		else:
			# Check the return code
			if process.returncode == 0:
				self.makefile_successfull = True
			else:
				self.log += "\nMake command failed with return code: {}".format(process.returncode)
				self.makefile_successfull = False

		self.makefile_log = stderr.decode('utf-8') if stderr else ''

		#print(stdout.decode('utf-8') if stdout else '')
		#print(stderr.decode('utf-8') if stderr else '')

	def run_make_clean(self):
		'''Run make clean in the working directory.'''
		command = ["make", "clean"]
		process = subprocess.Popen(command, cwd=self.mem_output_files_prefix, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		if self.verbose:
			print(stdout.decode('utf-8'))
			print(stderr.decode('utf-8'))

	def run(self, test_name):
		'''Run qtrvsim with the current configuration.'''
		#run qtrvsim with the given arguments, dump the output into the log string
		arguments = self.args + self.mem_arg + self.dump_mem_arg + self.uart_arg
		#print(self.args)
		#print(self.mem_arg)
		#print(self.dump_mem_arg)
		arguments = arguments.split()
		command = ["qtrvsim_cli"] + arguments + ["--asm", self.submission_file]
		
		if self.makefile_present:
			command = ["qtrvsim_cli"] + arguments + [self.submission_file.split(".")[0]]

		if self.verbose:
			print("Running command: ", ' '.join(command), "\n\n\n")
		
		killed = False

		try:
			process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdout, stderr = process.communicate(timeout=self.timeout_time)

		except subprocess.TimeoutExpired:
			process.kill()
			stdout, stderr = None, None
			killed = True
			self.log += f"\nKilled after {self.timeout_time} seconds."

		stdout_text =  "" if killed else stdout.decode('utf-8')
		stderr_text = f'Killed after {self.timeout_time} seconds.' if killed else stderr.decode('utf-8')

		if self.verbose:
			print(stdout_text)
			print(stderr_text)

		was_accepted = 0 #TODO: check if the output is correct

		if not killed:
			self.rgx_get_cycles(stdout_text)
			self.rgx_get_cache_stats(stdout_text)

			if self.do_compare_registers:
				self.rgx_get_registers(stdout_text)
				#compare registers
				for reg, value in self.compare_registes.items():
					if self.regs[reg] != value:
						was_accepted = 1

						if not self.is_private:
							self.log += f"\nregister {reg} does not match, \nexpected: {value},\ngot: {self.regs[reg]}\n"

			if self.do_compare_memory:
				self.read_mem_output_file()
				for addr, value in self.reference_memory.items():
					if self.mem[addr] != value:
						was_accepted = 1

						if not self.is_private:
							self.log += f"\nmemory at {addr} does not match, \nexpected: {value},\ngot: {self.mem[addr]}\n"

			if self.do_set_compare_uart:
				self.read_uart_file()
				differece = self.string_diff_and_hex(self.reference_uart, self.uart)

				if differece != '':
					was_accepted = 1

					if not self.is_private:
						self.log += f"\nUART does not match, \nexpected:\n{self.reference_uart}\ngot:\n{self.uart}\n"
						self.log += f"\nDifference:\n{differece}\n"


		if killed:
			self.result = 2
		else:
			self.result = was_accepted

		#save score metrics, -> cycles and cache stats
		self.scores["cycles"] = self.cycles #scoring metric for cycles
		self.scores["cache"] = self.cache_stats["i-cache:improved-speed"] #scoring metric for cache

		self.results[test_name] = (self.result, self.scores["cycles"], self.scores["cache"])

		self.mem_arg = ""
		self.dump_mem_arg = ""
		self.uart_arg = ""

		if self.verbose:
			print(self.get_log())