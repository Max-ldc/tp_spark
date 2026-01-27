from pyspark.sql import DataFrame

def load_data(df: DataFrame, output_path: str, format: str = "parquet"):
    """
    Saves the DataFrame to the specified path and displays a preview.
    """
    print(f"--- Saving data to {output_path} ---")
    
    # Write data
    writer = df.write.mode("overwrite")
    
    if format == "csv":
        writer.option("header", "true").csv(output_path)
    elif format == "parquet":
        writer.parquet(output_path)
    
    print(f"Data saved successfully.")
    
    # Print table length
    count = df.count()
    print(f"Table length: {count} rows")

    # Display a preview for "visual on processed data"
    print("--- Data Preview ---")
    df.show(20, truncate=False)