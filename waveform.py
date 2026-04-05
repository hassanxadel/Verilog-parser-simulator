import matplotlib

for _backend in ("TkAgg", "Qt5Agg", "QtAgg"):
    try:
        matplotlib.use(_backend, force=True)
        break
    except Exception:
        continue

import matplotlib.pyplot as plt


def plot_wave(signals):
    plt.figure()

    for i, (name, values) in enumerate(signals.items()):
        shifted = [v + i*2 for v in values]
        plt.step(range(len(values)), shifted, where='post')
        plt.text(len(values), i*2, name)

    plt.yticks([])
    plt.xlabel("Time")
    plt.title("Digital Waveform")
    plt.grid()

    plt.tight_layout()
    plt.show(block=True)