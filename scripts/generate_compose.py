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
      COORDINATOR_QUEUE: coordinator.year
      OUTPUT_EXCHANGE: articles_by_year
      PRE2020_QUEUE: articles_pre2020
      POST2020_QUEUE: articles_post2020
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
      COORDINATOR_QUEUE: coordinator.language
      INPUT_EXCHANGE: articles_by_year
      INPUT_ROUTING_KEY: article.pre2020
      OUTPUT_EXCHANGE: article_results
    depends_on:
      rabbitmq:
        condition: service_healthy
"""


def coordinator(stage, exchange, routing_keys=(), bindings=None):
    return f"""  coordinator_{stage}:
    build:
      context: .
      dockerfile: src/coordinator/Dockerfile
    environment:
      PYTHONUNBUFFERED: "1"
      MOM_HOST: rabbitmq
      INPUT_QUEUE: coordinator.{stage}
      OUTPUT_EXCHANGE: {exchange}
      OUTPUT_ROUTING_KEYS: '{','.join(routing_keys)}'
      OUTPUT_BINDINGS: '{json.dumps(bindings or {})}'
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
    depends_on:
      - gateway_1
{dependencies}
"""


def generate_compose(clients, year_filters, language_filters):
    services = ["services:\n", RABBITMQ]
    filter_names = [f"year-filter_{index}" for index in range(1, year_filters + 1)]
    filter_names += [f"language-filter_{index}" for index in range(1, language_filters + 1)]
    services.append(gateway())
    services.append(coordinator("year", "articles_by_year",
                                ("article.pre2020", "article.post2020"),
                                {"articles_pre2020": "article.pre2020", "articles_post2020": "article.post2020"}))
    services.append(coordinator("language", "article_results"))
    for index in range(1, year_filters + 1):
        services.append(year_filter(index))
    for index in range(1, language_filters + 1):
        services.append(language_filter(index))
    for index in range(1, clients + 1):
        services.append(client(index, filter_names + ["coordinator_year", "coordinator_language"]))
    return "".join(services)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clients", type=int, default=2, help="clients sharing one gateway (default: 2)")
    parser.add_argument("--year-filters", type=int, default=1, help="year workers (default: 1)")
    parser.add_argument("--language-filters", type=int, default=1, help="language workers (default: 1)")
    args = parser.parse_args()
    if args.clients < 0 or args.year_filters < 1 or args.language_filters < 1:
        parser.error("clients must be >= 0; year and language filters must be >= 1")

    contents = generate_compose(args.clients, args.year_filters, args.language_filters)
    output = PROJECT_ROOT / "docker-compose.yaml"
    output.write_text(contents, encoding="utf-8")
    print(f"Generated {output}: {args.clients} clients, 1 gateway, "
          f"{args.year_filters} year filters, {args.language_filters} language filters.")


if __name__ == "__main__":
    main()
