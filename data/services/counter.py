h_shift_min=0
h_shift_max=0.25
h_shift_step=0.05
v_shift_min=-0.1
v_shift_max=0.1
v_shift_step=0.05
zoom_min=0.05
zoom_max=0.25
zoom_step=0.05

def drange(start, stop, step):
    r = start
    while r <= stop:
        yield r
        r += step

counter = 0
for h_shift in drange(h_shift_min, h_shift_max, h_shift_step):
    for v_shift in drange(v_shift_min, v_shift_max, v_shift_step):
        for zoom_level in drange(zoom_min, zoom_max, zoom_step):
            counter += 1

print(counter)
print(len(list(drange(h_shift_min, h_shift_max, h_shift_step)))*len(list(drange(v_shift_min, v_shift_max, v_shift_step)))*len(list(drange(zoom_min, zoom_max, zoom_step))))

print(list(drange(h_shift_min, h_shift_max, h_shift_step)))
print(len(list(drange(h_shift_min, h_shift_max, h_shift_step))))
print(list(drange(v_shift_min, v_shift_max, v_shift_step)))
print(len(list(drange(v_shift_min, v_shift_max, v_shift_step))))
print(list(drange(zoom_min, zoom_max, zoom_step)))
print(len(list(drange(zoom_min, zoom_max, zoom_step))))

import numpy as np
print(np.arange(h_shift_min,h_shift_max+h_shift_step,h_shift_step))
print(len(np.arange(h_shift_min,h_shift_max+h_shift_step,h_shift_step)))
print(np.arange(v_shift_min, v_shift_max, v_shift_step))
print(len(np.arange(v_shift_min, v_shift_max, v_shift_step)))
print(np.arange(zoom_min, zoom_max, zoom_step))
print(len(np.arange(zoom_min, zoom_max, zoom_step)))