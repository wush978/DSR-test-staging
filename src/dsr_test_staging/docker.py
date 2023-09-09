import os
import shutil
from dataclasses import dataclass
from typing import ClassVar, List
import logging
import subprocess
from subprocess import CompletedProcess
from dsr_test_staging.config import settings
from dsr_test_staging.constants import R_LIB_DIRNAME
from dsr_test_staging.repo import ArchiveResult

logger = logging.getLogger(__name__)


@dataclass
class Docker:
    version: str
    archive_dir: str
    archive_results: List[ArchiveResult]
    r_lib_cache_dir: str
    
    TAG: ClassVar[str] = 'dsr-test-staging'
    
    def __post_init__(self):
        self.http_proxy = os.getenv('HTTP_PROXY', None)
        self.https_proxy = os.getenv('HTTPS_PROXY', None)
        self.r_lib = os.path.join(self.archive_dir, R_LIB_DIRNAME)
        os.mkdir(self.r_lib)
        if os.path.exists(os.path.join(self.r_lib_cache_dir, self.version)) and \
            settings.use_cache_r_lib :
            shutil.copytree(
                os.path.join(self.r_lib_cache_dir, self.version),
                os.path.join(self.r_lib, self.version),
            )
        for root, dirs, files in os.walk(self.r_lib):
            for dir in dirs:
                os.chmod(os.path.join(root, dir), 0o777)
            for file in files:
                os.chmod(os.path.join(root, file), 0o777)
        os.chmod(self.r_lib, 0o777)
    
    
    def generate(self) -> str:
        lines = [f'FROM rocker/r-ver:{self.version}']
        if self.http_proxy is not None:
            lines.append(
                f"""
RUN echo 'Acquire::http::Proxy "{self.http_proxy}";' > /etc/apt/apt.conf.d/80http_proxy
                """
            )
        if self.https_proxy is not None:
            lines.append(
                f"""
RUN echo 'Acquire::https::Proxy "{self.https_proxy}";' > /etc/apt/apt.conf.d/81https_proxy
                """
            )
        lines.append(
            f"""
RUN apt-get update && \
  apt-get install -y libxml2-dev libcurl4-openssl-dev libssl-dev \
      libpng-dev libjpeg-dev libgdal-dev
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
  echo "zh_TW.UTF-8 UTF-8" >> /etc/locale.gen && \
  echo "" >> /etc/locale.gen && \
  locale-gen && \
  update-locale
  
ENV LC_ALL=zh_TW.UTF-8
RUN useradd -u 110 -ms /bin/bash jenkins
VOLUME ["/home/jenkins/{R_LIB_DIRNAME}"]
WORKDIR /home/jenkins
COPY R/subprocess_0.8.3.tar.gz /home/jenkins
            """
        )
        for archive_result in self.archive_results:
            if archive_result.subdir is None:
                lines.append(
                    f'ADD {archive_result.repo}.tar /home/jenkins/{archive_result.repo}'
                )
            else:
                lines += [
                    f'ADD {archive_result.repo}.tar /home/jenkins/.{archive_result.repo}',
                    f'RUN mv /home/jenkins/.{archive_result.repo}/{archive_result.subdir} /home/jenkins/{archive_result.repo} && rm -rf /home/jenkins/.{archive_result.repo}',
                ]
        lines.append(
            f"""
ADD R/main.R /home/jenkins/main.R
RUN chown -R jenkins:jenkins /home/jenkins
USER jenkins
CMD ["/usr/local/bin/Rscript", "/home/jenkins/main.R"]
            """
        )
        with open(os.path.join(self.archive_dir, 'Dockerfile'), 'w') as fp:
                fp.write('\n'.join(lines))
                fp.write('\n')

    def build(self):
        cmd = [
            'docker', 'build',
            '-t', Docker.TAG,
        ]
        if self.http_proxy is not None:
            cmd += ['--build-arg', f'HTTP_PROXY={self.http_proxy}']
        if self.https_proxy is not None:
            cmd += ['--build-arg', f'HTTPS_PROXY={self.https_proxy}']
        cmd.append('.')
        logger.info(f'cmd: {cmd}')
        result = subprocess.run(
            args=cmd,
            cwd=self.archive_dir,
        )
        self.__check_return_code(result)

    def run(self):
        for test in settings.tests:
            logger.info(f'Testing {test.name}')
            cmd = ['docker', 'run', '--rm']
            if self.http_proxy is not None:
                cmd += ['-e', f'http_proxy={self.http_proxy}']
            if self.https_proxy is not None:
                cmd += ['-e', f'https_proxy={self.https_proxy}']
            cmd += ['-e', f'TEST_COURSE={test.test_course}']
            lesson_prefix = ','.join(test.lesson_prefix)
            cmd += ['-e', f'LESSON_PREFIX={lesson_prefix}']
            r_lib = os.path.join(
                os.getcwd(),
                self.archive_dir,
                R_LIB_DIRNAME
            )
            cmd += ['-v', f'{r_lib}:/home/jenkins/{R_LIB_DIRNAME}']
            if os.getenv('MAKE', None) is not None:
                make = os.getenv('MAKE')
                cmd += ['-e', f'MAKE="{make}"']
            cmd.append(Docker.TAG)
            logger.info(f'cmd: {cmd}')
            result = subprocess.run(
                args=cmd,
                cwd=self.archive_dir,
            )
            self.__check_return_code(result)

    def __check_return_code(self, result: CompletedProcess):
        if result.returncode != 0:
            raise RuntimeError(f'Error during executing args: {result.args}')
