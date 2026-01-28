import os
import platform

# Configuration pour Windows - DOIT être avant l'import de pyspark
if platform.system() == "Windows":
    os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-17"
    hadoop_home = os.path.join(os.path.expanduser("~"), "hadoop")
    hadoop_bin = os.path.join(hadoop_home, "bin")
    os.makedirs(hadoop_bin, exist_ok=True)
    os.environ["HADOOP_HOME"] = hadoop_home
    # Ajouter au PATH - IMPORTANT pour que Windows trouve hadoop.dll
    current_path = os.environ.get("PATH", "")
    if hadoop_bin not in current_path:
        os.environ["PATH"] = hadoop_bin + os.pathsep + current_path

from pyspark.sql import SparkSession


def get_spark_session(app_name: str) -> SparkSession:
    """
    Creates or gets a Spark Session.
    """
    builder = SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.sql.streaming.checkpointLocation", "./checkpoint")

    # Options pour Windows
    if platform.system() == "Windows":
        hadoop_home = os.path.join(os.path.expanduser("~"), "hadoop")
        hadoop_bin = os.path.join(hadoop_home, "bin")
        builder = builder \
            .config("spark.driver.extraJavaOptions",
                    f"-Dhadoop.home.dir={hadoop_home} -Djava.library.path={hadoop_bin}") \
            .config("spark.executor.extraJavaOptions",
                    f"-Dhadoop.home.dir={hadoop_home} -Djava.library.path={hadoop_bin}") \
            .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2") \
            .config("spark.sql.parquet.fs.optimized.committer.optimization-enabled", "false") \
            .config("spark.sql.sources.commitProtocolClass",
                    "org.apache.spark.sql.execution.datasources.SQLHadoopMapReduceCommitProtocol")

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    return spark