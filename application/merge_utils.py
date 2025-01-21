def join_csv_files(csv_file_1, csv_file_2, csv_file_3, output_file):
    import pandas as pd
    pd.set_option('future.no_silent_downcasting', True)

    try:
        # Load CSV files into DataFrames
        print("Loading CSV files...")
        df1 = pd.read_csv(csv_file_1)  # Weekly activity metrics
        df2 = pd.read_csv(csv_file_2)  # User profile data
        df3 = pd.read_csv(csv_file_3)  # Additional weekly metrics

        print(f"Loaded data shapes - df1: {df1.shape}, df2: {df2.shape}, df3: {df3.shape}")

        # Standardize column names (trim whitespaces and convert to lowercase)
        for df in [df1, df2, df3]:
            df.columns = df.columns.str.strip().str.lower()
            df['user_id'] = df['user_id'].astype(str).str.strip()

        # Process 'activity_week' column
        for df in [df1, df3]:
            if 'activity_week' in df.columns:
                df['activity_week'] = pd.to_datetime(df['activity_week'], errors='coerce').dt.strftime('%Y-%m-%d')
                df['activity_week'] = df['activity_week'].fillna('')

        # Rename df2 columns to add prefix
        df2_columns_to_rename = {
            col: f'df2_{col}' for col in df2.columns 
            if col not in ['user_id']
        }
        df2.rename(columns=df2_columns_to_rename, inplace=True)

        # Rename df3 columns to add prefix
        df3_columns_to_rename = {
            col: f'df3_{col}' for col in df3.columns 
            if col not in ['user_id', 'activity_week']
        }
        df3.rename(columns=df3_columns_to_rename, inplace=True)

        print("Getting unique weeks...")
        # Get all unique user_id and activity_week combinations
        weeks_df1 = df1[['user_id', 'activity_week']].copy()
        weeks_df3 = df3[['user_id', 'activity_week']].copy()

        print(f"Unique weeks in df1: {sorted(weeks_df1['activity_week'].unique())}")
        print(f"Unique weeks in df3: {sorted(weeks_df3['activity_week'].unique())}")

        all_weeks = pd.concat([weeks_df1, weeks_df3]).drop_duplicates()
        print(f"Total unique week combinations: {len(all_weeks)}")

        print("Merging data...")
        # Get user profile data
        user_profiles = df2.copy()

        # Merge all weeks with user profiles
        df_merged = pd.merge(all_weeks, user_profiles, on='user_id', how='left')
        print(f"After profile merge: {df_merged.shape}")

        # Merge with df1 for activity metrics
        df_merged = pd.merge(
            df_merged,
            df1,
            on=['user_id', 'activity_week'],
            how='left'
        )
        print(f"After df1 merge: {df_merged.shape}")

        # Merge with df3 for additional metrics
        df_merged = pd.merge(
            df_merged,
            df3,
            on=['user_id', 'activity_week'],
            how='left'
        )
        print(f"After df3 merge: {df_merged.shape}")

        print("Filling missing values...")
        # Fill activity metrics with 0
        activity_columns = [
            'total_uploads', 'total_licensing_submissions', 'total_sales_revenue',
            'total_num_of_sales', 'num_of_photos_featured', 'num_of_galleries_featured',
            'num_of_stories_featured', 'df3_photo_likes', 'df3_comments'
        ]
        
        for col in activity_columns:
            if col in df_merged.columns:
                df_merged[col] = df_merged[col].fillna(0)

        # Forward fill user profile data
        profile_columns = [
            'df2_full_name', 'df2_username', 'df2_user_type', 'df2_registration_date',
            'df2_membership', 'df2_country', 'df2_profile_url', 'df2_social_links',
            'df2_avg_lai_score', 'df2_exclusivity_rate', 'df2_acceptance_rate',
            'df3_avg_visit_days_monthly', 'df3_avg_aesthetic_score'
        ]

        print("Forward filling profile data...")
        # Group by user_id and forward fill profile data
        df_merged = df_merged.sort_values(['user_id', 'activity_week'])
        
        # Process profile columns in chunks for better performance
        chunk_size = 5
        for i in range(0, len(profile_columns), chunk_size):
            chunk = profile_columns[i:i + chunk_size]
            print(f"Processing columns {i+1}-{min(i+chunk_size, len(profile_columns))} of {len(profile_columns)}")
            
            existing_columns = [col for col in chunk if col in df_merged.columns]
            if existing_columns:
                # Store the user_id column
                user_id_col = df_merged['user_id'].copy()
                
                # Perform the forward/backward fill
                filled_data = df_merged.groupby('user_id')[existing_columns].transform('ffill')
                filled_data = filled_data.groupby(user_id_col).transform('bfill')
                
                # Update only the filled columns
                df_merged[existing_columns] = filled_data

        print("Removing blank activity weeks...")
        # Remove rows where activity_week is blank
        df_merged = df_merged[df_merged['activity_week'].notna() & (df_merged['activity_week'] != '')]

        print("Final sorting...")
        # Sort by user_id (numerically) and activity_week
        df_merged['user_id'] = pd.to_numeric(df_merged['user_id'])
        df_merged = df_merged.sort_values(['user_id', 'activity_week'])
        df_merged['user_id'] = df_merged['user_id'].astype(str)

        print("Saving results...")
        # Save the joined DataFrame to CSV
        df_merged.to_csv(output_file, index=False)
        print(f"Join results saved to {output_file}")

        print("\nFinal columns:", df_merged.columns.tolist())
        print("\nSample data:")
        print(df_merged[df_merged['user_id'] == '233'].sort_values('activity_week'))

    except Exception as e:
        print(f"Error during merge process: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise