def check_spike(input_list: list[int|float], spike_threshold: int|float) -> bool:
    """
    input_list: list of numbers to find spike in
    spike_threshold: threshold to determine spike in given input_list
    """
    for i, j in zip(input_list[:-1], input_list[1:]):
        if abs(j - i) > spike_threshold:
            return True
    return False
#
#
# a = [1,2,3,3,4,5,6,7,8,9,9,10,12,15,25,]
# b = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
#
# print(check_spike(a, 5))
# print(check_spike(b, 5))

import time

start_time = time.time()
while (time.time() - start_time) < 5:
    pass
    # print("/", end='\r')
    # print("-", end='\r')
    # print("\\", end='\r')


print()

print(time.time() - start_time)