import logging
import os
from dataclasses import dataclass
from typing import Iterable, Tuple
import git
from dsr_test_staging.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Repo:
    repo: str
    branch: str
    repos_dir: str
    
    @property
    def repo_dir(self) -> str:
        return os.path.join(
            self.repos_dir,
            self.repo,
        )
        
    @property
    def git_url(self) -> str:
        return f'https://github.com/wush978/{self.repo}.git'

    def __post_init__(self):
        if not os.path.exists(self.repo_dir):
            logger.info(f'clone from remote for repo: {self.repo}')
            git.Repo.clone_from(
                url=self.git_url,
                to_path=self.repo_dir,
                branch=self.branch,
            )
        self.git_repo = git.Repo(self.repo_dir)
        self.git_repo.remotes.origin.fetch()
        logger.info(f'checkout: origin/{self.branch}')
        if settings.checkout_target_repos:
            self.git_repo.git.checkout(f'origin/{self.branch}')

    def archive(self, archive_dir: str) -> Tuple[str, git.Commit]:
        fname = f'{self.repo}.tar'
        with open(os.path.join(archive_dir, fname), 'wb') as fp:
            self.git_repo.archive(fp, format='tar')
        return (self.repo, self.git_repo.commit())

    @staticmethod
    def run(repos_dir: str, archive_dir: str):
        result = {}
        for repo in Repo.from_settings(repos_dir=repos_dir):
            repo_name, commit = repo.archive(archive_dir=archive_dir)
            result[repo_name] = commit.hexsha[:7]
        return result

    @staticmethod
    def from_settings(repos_dir: str) -> Iterable['Repo']:
        for target_repo in settings.target_repos:
            for repo, branch in target_repo.items():
                yield Repo(repo=repo, branch=branch, repos_dir=repos_dir)
