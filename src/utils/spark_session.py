import os
import platform
from pyspark.sql import SparkSession

# Configuration pour Windows uniquement
if platform.system() == "Windows":
    os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-17"
    hadoop_home = os.path.join(os.path.expanduser("~"), "hadoop")
    hadoop_bin = os.path.join(hadoop_home, "bin")
    os.makedirs(hadoop_bin, exist_ok=True)
    os.environ["HADOOP_HOME"] = hadoop_home
    if hadoop_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = hadoop_bin + os.pathsep + os.environ.get("PATH", "")

def get_spark_session(app_name: str) -> SparkSession:
    """
    Creates or gets a Spark Session.
    """
    builder = SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.sql.streaming.checkpointLocation", "./checkpoint")

    # Options supplémentaires pour Windows
    if platform.system() == "Windows":
        hadoop_bin_path = os.path.join(os.path.expanduser("~"), "hadoop", "bin")
        builder = builder.config(
            "spark.driver.extraJavaOptions",
            f"-Djava.io.tmpdir=./tmp -Djava.library.path={hadoop_bin_path}"
        )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    return spark