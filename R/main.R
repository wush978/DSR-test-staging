loginfo <- function(fmt, ...) {
  cat(sprintf('(%s) ', Sys.time()))
  cat(sprintf(fmt, ...))
  cat('\n')
}

# Load args from env
loginfo('HTTP_PROXY: %s', Sys.getenv('HTTP_PROXY'))
loginfo('HTTPS_PROXY: %s', Sys.getenv('HTTPS_PROXY'))
R.version <- sprintf("%s.%s", R.version$major, R.version$minor)
loginfo('R.version: %s', R.version)
TEST_COURSE <- Sys.getenv("TEST_COURSE")
loginfo('TEST_COURSE: %s', TEST_COURSE)
LESSON_PREFIX <- Sys.getenv("LESSON_PREFIX")
loginfo('LESSON_PREFIX: %s', LESSON_PREFIX)


# Configure R_LIBS
if (Sys.info()["sysname"] == "Windows") {
  stop('TODO')
} else {
  R_LIBS <- c(file.path("R-lib", R.version))
}
lapply(R_LIBS, dir.create, recursive = TRUE, showWarnings = FALSE)
.libPaths(new = R_LIBS)
Sys.setenv("R_LIBS" = paste(R_LIBS, collapse = .Platform$file.sep))
loginfo('R_LIBS: %s', Sys.getenv('R_LIBS'))

# Install pvm
if (!suppressWarnings(require(remotes))) utils::install.packages("remotes", repos = "http://cran.csie.ntu.edu.tw", lib = R_LIBS[1])
utils::install.packages("pvm", repos = NULL, type = 'source', lib = R_LIBS[1])

# Install pvm-list
repos <- sprintf(
  'https://cran.microsoft.com/snapshot/%s',
  pvm::R.release.dates[R.version] + 14
)
names(repos) <- 'CRAN'
options(repos=repos)
loginfo('repos: %s', getOption('repos'))
write(
  c(
    sprintf("options(repos=c('CRAN' = '%s'))", repos), ""
  ),
  file = '/home/jenkins/.Rprofile'
)
pvm.list <- file.path('pvm-list', sprintf('dsr-%s.yml', R.version))
pvm::import.packages(
  pvm.list,
  repos = repos
)
utils::install.packages("swirl", repos = NULL, type = 'source', lib = R_LIBS[1])
if (!suppressWarnings(require(subprocess))) remotes::install_version("subprocess", "0.8.3", repos = 'https://cloud.r-project.org')
utils::install.packages("swirlify", repos = NULL, type = 'source', lib = R_LIBS[1])

Sys.setenv("SWIRL_DEV"="TRUE")
.libPaths(new = c(R_LIBS, .libPaths()))

lessons <- strsplit(LESSON_PREFIX, split = ",")[[1]]
for(lesson in lessons) {
  cat(sprintf("Test lesson: %s\n", lesson))
  swirlify::test_lesson_by_agent(
    TEST_COURSE,
    lesson,
    repos
  )
}
