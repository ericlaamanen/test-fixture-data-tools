#   Tool for taking load cell and string potentiometer data from DAQ unit from multiple test samples and plotting it.

import pandas as pd
from matplotlib import pyplot as plt
import glob2 as glob

path = r'C:\Users\elaam\PycharmProjects\069A_Fork_Test\2021-10-22_069A-data'
all_files = glob.glob(path + "/*.csv")

#   create empty dataframes for later
li = []
min_col_lengths = []
force_outputs = []

#   loop through all csv files in the folder at the specified path
for filename in all_files:

    #   import CSV with raw sensor data
    df_raw_data = pd.read_csv(filename, index_col=None, header=0, skiprows=7)
    gauge_voltage = df_raw_data['CHANNEL0']
    gauge_displacement = df_raw_data['CHANNEL1']

    #   create variables for scaling sensor data
    voltage_load_scale = 86.289     # lbf/V
    lbf_to_newtons = 4.44822    # N/lbf
    inches_to_mm = 25.4     # mm/in
    displacement_start = gauge_displacement[0]

    #   acquire test sample-ID from filename
    test_sample = filename.partition("_069A_")[2]

    #   create new column with voltage data converted to load in newtons and invert sign to flip curve
    df_raw_data['Load'] = gauge_voltage * voltage_load_scale * lbf_to_newtons * -1.0

    #   create new column with displacement data zeroed and sign flipped
    df_raw_data['Displacement'] = (gauge_displacement - displacement_start) * inches_to_mm * -1

    #   trim the load data such that only forward travel plotted
    #   loop through the data to find the index at which to data should be trimmed
    end_point = 0
    for i in range(len(df_raw_data['Load'])):
        if i > 500 and df_raw_data['Load'][i] <= 1:
            end_point = i
            break

    df_raw_data['Load'] = df_raw_data['Load'][0:end_point]

    #   trim the displacement data to same length of the load data
    df_raw_data['Displacement'] = df_raw_data['Displacement'][0:end_point]

    #   apply rolling average to the data to smooth out load-displacement curve
    df_raw_data['Load MA'] = df_raw_data['Load'].rolling(window=20, center=True, min_periods=5).mean()
    df_raw_data['Displacement MA'] = df_raw_data['Displacement'].rolling(window=20, center=True, min_periods=5).mean()

    #   displacement wasn't started at exactly zero each time -- offset data to account for this
    min_displacement = min(df_raw_data['Displacement MA'])
    df_raw_data['Displacement MA Offset'] = df_raw_data['Displacement MA'] - min_displacement
    load_moving_average = df_raw_data['Load MA']
    displacement_moving_average = df_raw_data['Displacement MA']
    displacement_moving_average_offset = df_raw_data['Displacement MA Offset']

    #   identify the position and magnitude of the peak static force (force right before static friction is overcome)
    static_end_pos = displacement_moving_average_offset.gt(0.5).idxmax()
    load_static = load_moving_average[:static_end_pos]
    load_max1 = max(load_static)
    load_max1 = round(load_max1, 2)
    max1_pos = load_static.idxmax()
    displacement_max1 = displacement_moving_average_offset[max1_pos]

    #   identify the magnitude of the average dynamic force
    dynamic_end_pos = displacement_moving_average_offset.gt(17).idxmax()
    load_dynamic = load_moving_average[static_end_pos:dynamic_end_pos]
    load_max2 = max(load_dynamic)
    load_max2 = round(load_max2, 2)
    max2_pos = load_dynamic.idxmax()
    displacement_max2 = displacement_moving_average_offset[max2_pos]
    dynamic_average = load_dynamic.mean(axis=0)
    dynamic_average = round(dynamic_average, 2)
    middle_pos = displacement_moving_average_offset.gt(9.5).idxmax()
    displacement_middle = displacement_moving_average_offset[middle_pos]

    fig, ax = plt.subplots()
    ax.plot(displacement_moving_average_offset, load_moving_average, label=test_sample[:-4])

    #   annotate static peak and dynamic average forces
    arrowprops=dict(arrowstyle="->")
    ax.annotate('static peak: ' + str(load_max1) + ' N', xy=(displacement_max1, load_max1), arrowprops=arrowprops, xytext=(0.2, 0.4), textcoords='axes fraction')
    ax.annotate('avg dynamic: ' + str(dynamic_average) + ' N', xy=(displacement_middle, dynamic_average), arrowprops=dict(arrowstyle="-"), xytext=(0.4, 0.7), textcoords='axes fraction')
    plt.legend(loc='lower right')
    plt.xlabel("Displacement (mm)")
    plt.ylabel("Force (N)")
    plt.savefig(str(test_sample) + '.png')

    #   remove unwanted data from dataframe
    clean_df = df_raw_data[['Load', 'Displacement', 'Load MA', 'Displacement MA', 'Displacement MA Offset']]
    clean_df.columns = ['Load (N) ' + test_sample, 'Displacement(mm) ' + test_sample, 'Load MA ' + test_sample,
                        'Displacement MA ' + test_sample, 'Displacement MA Offset ' + test_sample]

    #   trim column lengths all to same row number
    col_lengths = []
    for i in range(len(clean_df.columns)):
        col_lengths.append(clean_df[clean_df.columns[i]].count())

    #   create new local dataframe with calculated static and dynamic force data appended
    forces = pd.DataFrame(columns=['Sample ID', 'Peak Static Friction (N)', 'Avg Dynamic Friction (N)'], data=[[test_sample, load_max1, dynamic_average]])

    li.append(clean_df)
    min_col_lengths.append(min(col_lengths))
    force_outputs.append(forces)

plt.show()

#   append data to global dataframe with all samples combined
frame = pd.concat(li, axis=1, ignore_index=False)
force_data = pd.concat(force_outputs, axis=0, ignore_index=False)
frame = frame[:min(min_col_lengths)]

#   export two CSV files -- one with cleaned up and scaled sensor data, and one with forces of interest
frame.to_csv(r'C:\Users\elaam\PycharmProjects\069A_Fork_Test\2021-10-22_069A-data\compiled.csv', sep=',')
force_data.to_csv(r'C:\Users\elaam\PycharmProjects\069A_Fork_Test\2021-10-22_069A-data\forces.csv', sep=',')
