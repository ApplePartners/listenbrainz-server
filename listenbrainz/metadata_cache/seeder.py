from flask import current_app
from kombu import Connection, Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.metadata_cache.spotify.handler import SpotifyCrawlerHandler
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app


def submit_albums(connection, queue, message):
    """ Submit album ids to seed associated metadata cache """
    producer = connection.Producer()
    exchange = Exchange(current_app.config["EXTERNAL_SERVICES_EXCHANGE"], "topic", durable=True)
    producer.publish(
        message,
        routing_key=queue,
        exchange=exchange,
        delivery_mode=PERSISTENT_DELIVERY_MODE,
        declare=[exchange]
    )


def submit_new_releases_to_cache():
    """ Query spotify new releases for album ids and submit those to spotify metadata cache """
    app = create_app()
    with app.app_context():
        connection = Connection(
            hostname=current_app.config["RABBITMQ_HOST"],
            userid=current_app.config["RABBITMQ_USERNAME"],
            port=current_app.config["RABBITMQ_PORT"],
            password=current_app.config["RABBITMQ_PASSWORD"],
            virtual_host=current_app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

        current_app.logger.info("Searching new album ids to seed spotify metadata cache")
        spotify_handler = SpotifyCrawlerHandler(app)
        spotify_album_ids = spotify_handler.get_seed_albums()
        current_app.logger.info("Found %d album ids", len(spotify_album_ids))
        submit_albums(connection, spotify_handler.external_service_queue, {"spotify_album_ids": spotify_album_ids})
        current_app.logger.info("Submitted new release album ids")

        current_app.logger.info("Searching new album ids to seed spotify metadata cache")
        spotify_handler = SpotifyCrawlerHandler(app)
        album_ids = spotify_handler.get_seed_albums()
        current_app.logger.info("Found %d album ids", len(album_ids))
        submit_albums(connection, spotify_handler.external_service_queue, {"spotify_album_ids": album_ids})
        current_app.logger.info("Submitted new release album ids")
