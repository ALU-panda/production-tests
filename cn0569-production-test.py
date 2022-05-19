# This is the production test script for the EVAL-CN0569-PMDZ evaluation board from Analog Devices, Inc.
# Run this script in accordance with the corresponding test procedure document (18-066435-01).
# Do not edit any part of the code without consent from the Systems Development Group.
# - Allan Uy (29 Nov 2021)

# Import statements:
import adi
from math import sqrt
from serial.tools.list_ports import comports
from sys import exit
from time import sleep

# ADPD1080 PDx input settings (A = U1; B = U2):
pd_channels_A = (0,1,2,3)
pd_channels_B = (4,5,6,7)

# The following code is used to connect to the boards and configure the ADPD1080.
# This function automatically checks for the ADICUP3029 in the list of COM ports and connects to it.
# Returns SUCCESS when configuration is done.
def setup_adpd1080():
	global adpd1080
	mbed_serial_port = ''
	
	com_ports_list = list(comports())
	for n in range(len(com_ports_list)):
		if com_ports_list[n].manufacturer == 'mbed':
			mbed_serial_port = com_ports_list[n].device
			break
	
	if mbed_serial_port == '':
		print('\nUnable to connect to the ADICUP3029. Please recheck hardware connections and try again.')
		exit(1)
	
	adpd1080 = adi.adpd1080(uri='serial:' + str(mbed_serial_port) + ',115200,8n1n')
	adpd1080._ctrl.context.set_timeout(0)
	adpd1080.rx_buffer_size = 8
	adpd1080.sample_rate = 10
	avg = [0, 0, 0, 0, 0, 0, 0, 0]
	
	for _ in range(5):
		data = adpd1080.rx()
        
	for idx, val in enumerate(data):
			avg[idx] += val.sum()
			
	avg = [int(x / 5) for x in avg]

	for i in range(8):
		adpd1080.channel[i].offset = adpd1080.channel[i].offset + avg[i]

	adpd1080.sample_rate = 512
	return 'SUCCESS'

# The following code is used to test the gesture detection.
# This function reads the data from U1 or U2 and runs an algorithm to determine the gesture detected.
# The detected gesture must match indicated the hand movement. A maximum of 10 failures are allowed for each test.
# Returns SUCCESS if there is no discrepancy between the algorithm result and the expected result.
def sense_gesture(pd_test, target_gest):
	g_incr = 0
	fail_count = 0
	pd_test_data = [0,0,0,0]
	has_gest = False
	algo_time = False
	
	if target_gest == 'CLICK':
		print('\nTesting "' + str(target_gest) + '" gesture detection using U' + str(pd_test + 1) + '. Hold your hand over U' + str(pd_test + 1) + ' and then slowly move it toward the evaluationboard.')
	
	else:
		print('\nTesting "' + str(target_gest) + '" gesture detection using U' + str(pd_test + 1) + '. Hold your hand over the evaluation board and then slowly move it ' + str(target_gest) + ' across U' + str(pd_test + 1) + '.')
	
	while True:
		data = adpd1080.rx()
		if pd_test == 0:
			pd_test_data = [data[0].sum(), data[1].sum(), data[2].sum(), data[3].sum()]
			
		else:
			pd_test_data = [data[4].sum(), data[5].sum(), data[6].sum(), data[7].sum()]
			
		L = pd_test_data[0] + pd_test_data[1] + pd_test_data[2] + pd_test_data[3]
		
		if L > 1000 and not has_gest:
			has_gest = True
			start_x = (int(pd_test_data[1]) - int(pd_test_data[0])) / (int(pd_test_data[1]) + int(pd_test_data[0]))
			start_y = (int(pd_test_data[3]) - int(pd_test_data[2])) / (int(pd_test_data[3]) + int(pd_test_data[2]))
			
		if L < 1000 and has_gest and g_incr >= 5:
			has_gest = False
			try:
				end_x = (int(pd_test_data[1]) - int(pd_test_data[0])) / (int(pd_test_data[1]) + int(pd_test_data[0]))
				end_y = (int(pd_test_data[3]) - int(pd_test_data[2])) / (int(pd_test_data[3]) + int(pd_test_data[2]))
				
			except ZeroDivisionError:
				end_x = 0.000001
				end_y = 0.000001
				
			algo_time = True

		if L >= 1000:
			g_incr += 1
			
		else:
			g_incr = 0

		if algo_time:
			algo_time = False
			m = (start_y - end_y) / (start_x - end_x + 0.000001)
			d = sqrt((start_x - end_x)**2 + (start_y - end_y)**2)
			
			if d < 0.07 and target_gest == 'CLICK':
				print('   U' + str(pd_test + 1) + ' "' + str(target_gest) + '" gesture detection successful.')
				return 'SUCCESS'
				
			else:
				if abs(m) > 1:
					if start_y < end_y and target_gest == 'UP':
						print('   U' + str(pd_test + 1) + ' "' + str(target_gest) + '" gesture detection successful.')
						return 'SUCCESS'
						
					elif start_y > end_y and target_gest == 'DOWN':
						print('   U' + str(pd_test + 1) + ' "' + str(target_gest) + '" gesture detection successful.')
						return 'SUCCESS'
						
					else:
						print('   Wrong gesture detected (expected: "' + str(target_gest) + '"). Please try again.')
						fail_count = fail_count + 1
                
				elif abs(m) < 1:
					if start_x < end_x and target_gest == 'RIGHT':
						print('   U' + str(pd_test + 1) + ' "' + str(target_gest) + '" gesture detection successful.')
						return 'SUCCESS'
                    
					elif start_x > end_x and target_gest == 'LEFT':
						print('   U' + str(pd_test + 1) + ' "' + str(target_gest) + '" gesture detection successful.')
						return 'SUCCESS'
						
					else:
						print('   Wrong gesture detected (expected: "' + str(target_gest) + '"). Please try again.')
						fail_count = fail_count + 1
                
				else:
					print('   Gesture data is unreliable (expected: "' + str(target_gest) + '"). Please try again.')
		
		if fail_count > 10:
			print('\nGesture detection FAILED! Please check if there are any obstructions in front of U' + str(pd_test + 1) + ' and try again.\n')
			exit(1)
		
# The following code is the start of the main test.
# Operators should follow the promprts that will display on their console.
def main():
	print('\nThis test script will now test for gesture detection on the EVAL-CN0569-PMDZ.\nPlease ensure that there are no objects in the immediate surroundings of the boards.')
	
	while True:
		print('\nDo you wish to continue? (yes/no):', end = ' ')
		start_test = input()

		if start_test.lower() == 'no' or start_test.lower() == 'n':
			print('\nAborting test...\n')
			sleep(1)
			exit(1)

		elif start_test.lower() == 'yes' or start_test.lower() == 'y':
			print('\nConfiguring the ADPD1080. Please wait....')
			setup_adpd1080()
			
			print('\nGesture detection algorithm is now running. Please perform the appropriate hand movement when prompted.')
			
			sense_gesture(0,'LEFT')
			sleep(1)
			sense_gesture(1,'LEFT')
			sleep(1)
			
			sense_gesture(0,'RIGHT')
			sleep(1)
			sense_gesture(1,'RIGHT')
			sleep(1)
			
			sense_gesture(0,'UP')
			sleep(1)
			sense_gesture(1,'UP')
			sleep(1)
			
			sense_gesture(0,'DOWN')
			sleep(1)
			sense_gesture(1,'DOWN')
			sleep(1)
			
			sense_gesture(0,'CLICK')
			sleep(1)
			sense_gesture(1,'CLICK')
			sleep(1)
			
			print('\nGesture detection PASSED! Test script has finished.\n')
			return 0
		
		else:
			print('\nPlease answer with a yes or no.')
		
if __name__ == "__main__":
	main()
	exit(0)
