from collections import defaultdict
import os
import shutil
import arrow
import click
from dsr_test_staging.config import settings
import logging
from dsr_test_staging.docker import Docker
from dsr_test_staging.init_logging import init_logging
from dsr_test_staging.repo import Repo
from dsr_test_staging.constants import R_LIB_DIRNAME
import json
from dotenv import load_dotenv


logger = logging.getLogger(__name__)
load_dotenv()


@click.group()
def cli():
    pass


@cli.command()
def list_versions():
    for version in settings.target_versions:
        print(version)


@cli.command()
@click.option(
    '--output', '-o',
    type=str,
    default='',
    required=True
)
@click.option(
    '--version', '-v',
    type=str,
    default='',
    required=False,
)
def test_dsr(output, version):
    results = defaultdict(dict)
    if version == '':
        versions = settings.target_versions
    else:
        versions = [version]
    for version in versions:
        results[version] = {}
        try:            
            results[version]['archives'] = test_dsr_version(version)
            results[version]['pass'] = True
        except Exception:
            logger.exception('error')
            results[version]['pass'] = False
    with open(output, 'w') as fp:
        fp.write(json.dumps(results))


def test_dsr_version(version):
    init_logging()
    r_lib_cache_dir = os.path.join(
        settings.docker_dir,
        R_LIB_DIRNAME,
    )
    archive_dir = os.path.join(
        settings.docker_dir,
        f't{arrow.now().int_timestamp}',
    )
    os.mkdir(archive_dir)
    # deploy repos
    logger.info(f'Deploy repos from: {settings.repos_dir} to: {archive_dir}')
    archive_results = Repo.run(
        repos_dir=settings.repos_dir,
        archive_dir=archive_dir,
    )
    logger.info(f'{archive_results}')
    # copy R script and subprocess
    ensure_subprocess()
    shutil.copytree('R', os.path.join(archive_dir, 'R'))
    # init Dockerfile
    docker = Docker(
        version=version,
        archive_dir=archive_dir,
        archive_results=archive_results,
        r_lib_cache_dir=r_lib_cache_dir,
    )
    docker.generate()
    # build docker
    docker.build()
    # test courses
    docker.run()
    return [
        {'repo': archive_result.repo, 'commit': archive_result.commit.hexsha}
        for archive_result in archive_results
    ]


def ensure_subprocess():
    if os.path.exists('R/subprocess_0.8.3.tar.gz'):
        return
    import urllib.request
    src_url = 'https://cran.r-project.org/src/contrib/Archive/' + \
        'subprocess/subprocess_0.8.3.tar.gz'
    urllib.request.urlretrieve(
        src_url,
        filename='R/subprocess_0.8.3.tar.gz',
    )

    
if __name__ == '__main__':
    cli()