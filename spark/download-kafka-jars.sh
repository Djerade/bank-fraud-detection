#!/usr/bin/env bash
# Télécharge les JAR nécessaires au connecteur Kafka SQL (évite --packages au runtime = moins d’échecs réseau).
set -euo pipefail
J="$SPARK_HOME/jars"
mkdir -p "$J"
cd "$J"
MV=https://repo1.maven.org/maven2
fetch() {
  local url=$1
  local name
  name=$(basename "$url")
  if [[ ! -f "$name" ]]; then
    echo "fetch $name"
    wget -q -O "$name" "$url"
  fi
}
fetch "$MV/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.3/spark-sql-kafka-0-10_2.12-3.5.3.jar"
fetch "$MV/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.3/spark-token-provider-kafka-0-10_2.12-3.5.3.jar"
fetch "$MV/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar"
fetch "$MV/org/lz4/lz4-java/1.8.0/lz4-java-1.8.0.jar"
fetch "$MV/org/xerial/snappy/snappy-java/1.1.10.5/snappy-java-1.1.10.5.jar"
fetch "$MV/org/slf4j/slf4j-api/2.0.7/slf4j-api-2.0.7.jar"
fetch "$MV/org/apache/hadoop/hadoop-client-runtime/3.3.4/hadoop-client-runtime-3.3.4.jar"
fetch "$MV/org/apache/hadoop/hadoop-client-api/3.3.4/hadoop-client-api-3.3.4.jar"
fetch "$MV/commons-logging/commons-logging/1.1.3/commons-logging-1.1.3.jar"
fetch "$MV/com/google/code/findbugs/jsr305/3.0.0/jsr305-3.0.0.jar"
fetch "$MV/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar"
echo "Kafka connector JARs OK in $J"
