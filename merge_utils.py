def join_csv_files(csv_file_1, csv_file_2, csv_file_3, output_file):
    import pandas as pd

    # Load CSV files into DataFrames
    df1 = pd.read_csv(csv_file_1)
    df2 = pd.read_csv(csv_file_2)
    df3 = pd.read_csv(csv_file_3)

    # Standardize column names (trim whitespaces and convert to lowercase)
    for df in [df1, df2, df3]:
        df.columns = df.columns.str.strip().str.lower()

    # Ensure 'user_id' is a string in all DataFrames
    for df in [df1, df2, df3]:
        df['user_id'] = df['user_id'].astype(str).str.strip()

    # Process 'activity_week' column
    for df in [df1, df2, df3]:
        if 'activity_week' in df.columns:
            df['activity_week'] = pd.to_datetime(df['activity_week'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['activity_week'] = df['activity_week'].fillna('')
        else:
            df['activity_week'] = ''

    # Rename columns in df2 and df3 to prevent overlaps
    df2_columns_to_rename = {col: f'df2_{col}' for col in df2.columns if col not in ['user_id', 'activity_week']}
    df2.rename(columns=df2_columns_to_rename, inplace=True)

    df3_columns_to_rename = {col: f'df3_{col}' for col in df3.columns if col not in ['user_id', 'activity_week']}
    df3.rename(columns=df3_columns_to_rename, inplace=True)

    # Merge on 'user_id' and 'activity_week' using outer joins
    df_merged = pd.merge(df1, df2, on=['user_id', 'activity_week'], how='outer')
    df_merged = pd.merge(df_merged, df3, on=['user_id', 'activity_week'], how='outer')

    # Create DataFrames without 'activity_week' to fill missing data
    df1_user = df1.drop(columns=['activity_week']).drop_duplicates(subset=['user_id'])
    df2_user = df2.drop(columns=['activity_week']).drop_duplicates(subset=['user_id'])
    df3_user = df3.drop(columns=['activity_week']).drop_duplicates(subset=['user_id'])

    # Set 'user_id' as index for updating
    df_merged.set_index('user_id', inplace=True)
    df1_user.set_index('user_id', inplace=True)
    df2_user.set_index('user_id', inplace=True)
    df3_user.set_index('user_id', inplace=True)

    # Update df_merged with user-level data
    df_merged.update(df1_user, overwrite=False)
    df_merged.update(df2_user, overwrite=False)
    df_merged.update(df3_user, overwrite=False)

    # Reset index to bring 'user_id' back as a column
    df_merged.reset_index(inplace=True)

    # Fill NaN values with zeros or appropriate defaults
    df_merged.fillna(0, inplace=True)

    # Filter out rows with blank activity_week
    df_merged = df_merged[df_merged['activity_week'].notna() & (df_merged['activity_week'] != '')]
    print("Removed rows with blank activity_week values")

    # Save the joined DataFrame to CSV
    df_merged.to_csv(output_file, index=False)
    print(f"Join results saved to {output_file}")

    # Debugging: print sample data
    print("\nSample data from df_merged:")
    print(df_merged.head())
