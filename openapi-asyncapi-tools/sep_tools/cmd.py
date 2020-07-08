import click
import logging

from .EventPortal import EventPortal

logging.basicConfig(level=logging.INFO)

@click.group()
@click.version_option()
def cli():
    pass

# -------------------------- importOpenAPI --------------------------
@cli.command(name="importOpenAPI")
@click.argument('open_api_spec_file', type=click.Path(exists=True))
@click.option('--domain', default="TestDomain", show_default=True, 
    help='Application Domain')
@click.option('--pub', default=False, show_default=True, is_flag=True,
    help='Publish all related events insted of subscribe on them')
@click.option('--application', default="TestApp", show_default=True,
    help='Application')
@click.option('--token', envvar='EVENT_PORTAL_TOKEN', required=True,
    help="The API token of Solace's Cloud REST API, could be set with env variable [EVENT_PORTAL_TOKEN]")
def cmdImportOpenAPI(open_api_spec_file, domain, pub, application, token):
    """Generate an Application based on the specified OpenAPI 3.0 specification by
    subscribing on all related events"""

    logging.info("Import file '{}' to build Application '{}' within Domain '{}'".format(
        open_api_spec_file, application, domain
    ))
    ep = EventPortal(token, pub)
    ep.importOpenAPISpec(open_api_spec_file, domain, application)

# -------------------------- importOpenAPI --------------------------
@cli.command(name="createQueue")
@click.argument('open_api_spec_file', type=click.Path(exists=True))
@click.option('--admin-user', default='admin', show_default=True,
    help='The username of the management user')
@click.option('--admin-password', default='admin', show_default=True,
    envvar='SOL_ADMIN_PWD', help='The password of the management user, could be set by env variable [SOL_ADMIN_PWD]')
@click.option('--host', default='http://localhost:8080', show_default=True,
    help='URL to access the management endpoint of the broker')
@click.option('--vpn', default='default', show_default=True,
    help='The name of the message vpn')
@click.option('--queue', required=True,
    help='The name of the queue to create')
def createQueue(open_api_spec_file, admin_user, admin_password, host, vpn, queue):
    """Generate a queue based on the specified OpenAPI 3.0 specification by
    subscribing on all related events"""

    if host[-1]=='/':
        host=host[:-1]

    logging.info("Import file '{}' to build a queue '{}' on the broker '{}'".format(
        open_api_spec_file, queue, host))
    ep = EventPortal(admin_user=admin_user,
        admin_password=admin_password,
        host=host,
        vpn=vpn,
        queueName=queue,)
    ep.createQueue(open_api_spec_file)

# -------------------------- generateAsyncAPI --------------------------
@cli.command(name="generateAsyncAPI")
@click.argument('application')
@click.option('--token', envvar='EVENT_PORTAL_TOKEN', required=True,
    help="The API token of Solace's Cloud REST API, could be set with env variable [EVENT_PORTAL_TOKEN]")
def generateAsyncAPI(application, token):
    """Generate an AsyncAPI spec for the specified Application"""

    logging.info("Generate AsyncAPI spec for the Application '{}'".format(
         application
    ))
    ep = EventPortal(token)
    ep.generateAsyncApi(application)

# -------------------------- generateOpenAPI --------------------------
@cli.command(name="generateOpenAPI")
@click.argument('domain-name')
@click.option('--token', envvar='EVENT_PORTAL_TOKEN', required=True,
    help="The API token of Solace's Cloud REST API, could be set with env variable [EVENT_PORTAL_TOKEN]")
def generateOpenApi(domain_name, token):
    """Generate a OpenAPI spec for the specified Domain that represents all the external events that the domain receives"""

    logging.info("Generate OpenAPI spec for the Application Domain '{}'".format(
         domain_name
    ))
    ep = EventPortal(token)
    ep.generateOpenApi(domain_name)


if __name__ == '__main__':
    cli()