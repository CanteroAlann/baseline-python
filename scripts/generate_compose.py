import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RABBITMQ = """  rabbitmq:
    build:
      context: .
      dockerfile: src/rabbitmq/Dockerfile
    ports:
      - "127.0.0.1:15672:15672"
    environment:
      RABBITMQ_LOG_LEVELS: error
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_port_connectivity"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 50s
"""

def gateway():
    return """  gateway_1:
    build:
      context: .
      dockerfile: src/gateway/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      SERVER_HOST: 0.0.0.0
      SERVER_PORT: "5000"
      MOM_HOST: rabbitmq
      RESULT_EXCHANGE: article_results
      OUTPUT_QUEUE: articles
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def year_filter(index):
    return f"""  year-filter_{index}:
    build:
      context: .
      dockerfile: src/filters/year_filter/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: articles
      CONTROL_QUEUE: control.year
      OUTPUT_EXCHANGE: articles_by_year
      PRE2020_QUEUE: articles_pre2020
      PREPROCESS_QUEUE: articles_to_preprocess
      PREPROCESS_ROUTING_KEY: article.*
      BIOGRAPHY_QUEUE: articles_biography
      PRE2020_ROUTING_KEY: article.pre2020
      POST2020_ROUTING_KEY: article.post2020
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def language_filter(index):
    return f"""  language-filter_{index}:
    build:
      context: .
      dockerfile: src/filters/language_filter/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: articles_pre2020
      CONTROL_QUEUE: control.language
      INPUT_EXCHANGE: articles_by_year
      INPUT_ROUTING_KEY: article.pre2020
      OUTPUT_EXCHANGE: article_results
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def coordinator(stage, exchange, routing_keys=(), bindings=None, query_id=None, *, independent_routes=False,
                expected_inputs=None, input_queue=None):
    options = '      INDEPENDENT_ROUTES: "true"\n' if independent_routes else ""
    if expected_inputs is not None:
        options += f'      EXPECTED_INPUTS: "{expected_inputs}"\n'
    return f"""  coordinator_{stage}:
    build:
      context: .
      dockerfile: src/coordinator/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: {input_queue or f'control.{stage}'}
      OUTPUT_EXCHANGE: {exchange}
      OUTPUT_ROUTING_KEYS: '{','.join(routing_keys)}'
      OUTPUT_BINDINGS: '{json.dumps(bindings or {})}'
      QUERY_ID: '{query_id or ''}'
{options}    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def biography_filter(index):
    return f"""  biography-filter_{index}:
    build:
      context: .
      dockerfile: src/filters/biography_filter/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: articles_biography
      COORDINATOR_QUEUE: coordinator.biography
      OUTPUT_QUEUE: q2_image_requests
      INPUT_EXCHANGE: articles_by_year
      INPUT_ROUTING_KEY: article.pre2020
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def image_fetcher(index):
    return f"""  image-fetcher_{index}:
    build:
      context: .
      dockerfile: src/filters/image_fetcher/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: q2_image_requests
      OUTPUT_EXCHANGE: article_results
      IMAGE_FETCH_TIMEOUT: "15"
      IMAGE_MAX_BYTES: "20971520"
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def client(index, filter_names):
    dependencies = "\n".join(f"      - {name}" for name in filter_names)
    return f"""  client_{index}:
    build:
      context: .
      dockerfile: src/client/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      INPUT_FILE: /data/file{index}.csv
      SERVER_HOST: gateway_1
      SERVER_PORT: "5000"
    volumes:
      - ./samples:/data:ro
      - ./output/client_{index}:/output
    depends_on:
      - gateway_1
{dependencies}
"""


def preprocess(index):
    return f"""  preprocess_{index}:
    build:
      context: .
      dockerfile: src/preprocess/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: articles_to_preprocess
      INPUT_EXCHANGE: articles_by_year
      INPUT_ROUTING_KEY: article.*
      OUTPUT_EXCHANGE: preprocessed_articles
      CONTROL_QUEUE: control.preprocess
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def q5_word_count(index, branch, shard_count):
    queue_name = "preprocessed_pre2020" if branch == "historical" else "preprocessed_post2020"
    routing_key = "article.pre2020" if branch == "historical" else "article.post2020"
    output_exchange = "q5.historical.counts" if branch == "historical" else "q5.candidate.counts"
    return f"""  q5-{branch}-words_{index}:
    build:
      context: .
      dockerfile: src/word_count/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: {queue_name}
      INPUT_EXCHANGE: preprocessed_articles
      INPUT_ROUTING_KEY: {routing_key}
      OUTPUT_EXCHANGE: {output_exchange}
      CONTROL_QUEUE: control.q5_{branch}_words
      BRANCH: {branch}
      SHARD_COUNT: "{shard_count}"
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def q5_historical(shard_id):
    return f"""  q5-historical_{shard_id + 1}:
    build:
      context: .
      dockerfile: src/historical/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: q5.historical.{shard_id}
      INPUT_EXCHANGE: q5.historical.counts
      INPUT_ROUTING_KEY: q5.historical.{shard_id}
      OUTPUT_QUEUE: q5.historical.reducer
      SHARD_ID: "{shard_id}"
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def q5_candidate(shard_id):
    return f"""  q5-candidate_{shard_id + 1}:
    build:
      context: .
      dockerfile: src/candidate/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: q5.candidate.{shard_id}
      INPUT_EXCHANGE: q5.candidate.counts
      INPUT_ROUTING_KEY: q5.candidate.{shard_id}
      AVERAGE_EXCHANGE: q5.average
      RESULT_EXCHANGE: article_results
      CONTROL_QUEUE: control.q5_done
      SHARD_ID: "{shard_id}"
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def q5_historical_reducer(historical_shards, candidate_shards):
    return f"""  q5-historical-reducer:
    build:
      context: .
      dockerfile: src/historical_reducer/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: q5.historical.reducer
      OUTPUT_EXCHANGE: q5.average
      HIST_SHARD_COUNT: "{historical_shards}"
      CANDIDATE_SHARD_COUNT: "{candidate_shards}"
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def generate_compose(clients, year_filters, language_filters, q5_word_workers=5,
                     historical_shards=5, candidate_shards=5, preprocess_workers=5):
    services = ["services:\n", RABBITMQ]
    filter_names = [f"year-filter_{index}" for index in range(1, year_filters + 1)]
    filter_names += [f"language-filter_{index}" for index in range(1, language_filters + 1)]
    filter_names += ["biography-filter_1", "image-fetcher_1"]
    services.append(gateway())
    services.append(coordinator("year", "articles_by_year",
                                ("article.pre2020", "article.post2020"),
                                {"articles_pre2020": "article.pre2020", "articles_to_preprocess": "article.*", "articles_biography": "article.pre2020"}))
    services.append(coordinator("language", "article_results", query_id=1))
    services.append(coordinator("preprocess", "preprocessed_articles",
                                ("article.pre2020", "article.post2020"),
                                {"preprocessed_pre2020": "article.pre2020",
                                 "preprocessed_post2020": "article.post2020"}, independent_routes=True))
    filter_names.append("coordinator_preprocess")
    for branch, count in [("historical", historical_shards), ("candidate", candidate_shards)]:
        routes = tuple(f"q5.{branch}.{shard_id}" for shard_id in range(count))
        output_exchange = "q5.historical.counts" if branch == "historical" else "q5.candidate.counts"
        services.append(coordinator(f"q5_{branch}_words", output_exchange, routes,
                                    {route: route for route in routes}))
        filter_names.append(f"coordinator_q5_{branch}_words")
    services.append(coordinator("biography", "q2_image_requests_exchange",
                                ("q2.images",), {"q2_image_requests": "q2.images"}))
    for index in range(1, year_filters + 1):
        services.append(year_filter(index))
    for index in range(1, language_filters + 1):
        services.append(language_filter(index))
    for index in range(1, preprocess_workers + 1):
        services.append(preprocess(index))
        filter_names.append(f"preprocess_{index}")
    for branch, count in [("historical", historical_shards), ("candidate", candidate_shards)]:
        for index in range(1, q5_word_workers + 1):
            name = f"q5-{branch}-words_{index}"
            services.append(q5_word_count(index, branch, count))
            filter_names.append(name)
    for shard_id in range(historical_shards):
        services.append(q5_historical(shard_id))
        filter_names.append(f"q5-historical_{shard_id + 1}")
    for shard_id in range(candidate_shards):
        services.append(q5_candidate(shard_id))
        filter_names.append(f"q5-candidate_{shard_id + 1}")
    services.append(q5_historical_reducer(historical_shards, candidate_shards))
    services.append(coordinator("q5_final", "article_results", query_id=5,
                                expected_inputs=candidate_shards, input_queue="control.q5_done"))
    filter_names += ["q5-historical-reducer", "coordinator_q5_final"]
    services.append(biography_filter(1))
    services.append(image_fetcher(1))
    for index in range(1, clients + 1):
      services.append(client(index, filter_names + [
        "coordinator_year", "coordinator_language", "coordinator_biography",
      ]))
    return "".join(services)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clients", type=int, default=1, help="clients sharing one gateway (default: 3)")
    parser.add_argument("--year-filters", type=int, default=3, help="year workers (default: 3)")
    parser.add_argument("--language-filters", type=int, default=3, help="language workers (default: 3)")
    parser.add_argument("--preprocess-workers", type=int, default=3, help="shared preprocessing workers for both year branches")
    parser.add_argument("--q5-word-workers", type=int, default=3, help="word-count workers per Q5 branch")
    parser.add_argument("--q5-historical-shards", type=int, default=3)
    parser.add_argument("--q5-candidate-shards", type=int, default=3)
    args = parser.parse_args()
    if args.clients < 0 or min(args.year_filters, args.language_filters, args.q5_word_workers,
                               args.q5_historical_shards, args.q5_candidate_shards, args.preprocess_workers) < 1:
        parser.error("clients must be >= 0; worker and shard counts must be >= 1")

    contents = generate_compose(args.clients, args.year_filters, args.language_filters,
                                args.q5_word_workers, args.q5_historical_shards, args.q5_candidate_shards,
                                args.preprocess_workers)
    output = PROJECT_ROOT / "docker-compose.yaml"
    output.write_text(contents, encoding="utf-8")
    print(f"Generated {output}: {args.clients} clients, 1 gateway, "
          f"{args.preprocess_workers} preprocessing workers, "
          f"{args.q5_word_workers} Q5 word-count workers, "
          f"{args.q5_historical_shards} Q5 historical shards, "
          f"{args.q5_candidate_shards} Q5 candidate shards, "
          f"{args.year_filters} year filters, {args.language_filters} language filters, 1 biography filter, 1 image fetcher")


if __name__ == "__main__":
    main()
