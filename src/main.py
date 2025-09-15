#fastf1_main.py
import fastf1 as ff1
import pandas as pd
import os #import os mojure to being folder management

# Create a cache directory if it doesn't exist
cache_dir = './cache'  # Define a cache directory
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)  # Create the cache directory if it doesn't exist
    print(f"Cache directory created at: {cache_dir}")
# Enable caching in FastF1
ff1.Cache.enable_cache(cache_dir)
print(f"FastF1 cache enabled at: {cache_dir}")
# Example: Load a session and print some data

# Load a specific session
year = 2023
GP = 'Japan'
session = 'R'# You can change this to 'Practice 1', 'Practice 2', 'Practice 3', or 'Qualifying'

print(f"\nloading session data for {year} {GP} Grand Prix...")
try:
    session_data = ff1.get_session(year, GP, session)
    # Load the session data
    # You can add teremetrys such as weather, laps, etc though "load" function
    session_data.load()  # This may take some time if not cached
    print("Session data loaded successfully!")
except Exception as e:
    print(f"Error loading session data: {e}")
    # Handle the error appropriately
    exit(1)

#You can access all driver data as DataFrame in session.laps
laps_df = session_data.laps
print(f"\nLap data retrieved. Processing data...")
# Display the first few rows of the laps DataFrame

#chose a most important columns to strategic analysis
columns_to_save = [
    'Driver',
    'LapNumber',
    'LapTime',
    'Compound',
    'Stint',
    'TyreLife',
    'Position'
]

#LapTime is Timedelta type, so we change from Timedelta to float tipe
#we access Timedelta property by .dt accessor
laps_df['LapTimeSeconds'] = laps_df['LapTime'].dt.total_seconds()

#create a new DataFrame with selected columns
output_df = laps_df[columns_to_save]

# Save the DataFrame to a CSV file
output_filename = f'lap_times_{year}_{GP}_{session.lower()}.csv'
output_df.to_csv(output_filename, index=False)

print(f"\nDataFrame head:")
print(output_df.head().to_markdown(index=False))
#You can display it  cleanly at terminal by using ".to_markdown()"

print(f"\nSuccessfully saved lap times to {output_filename}")