# install the Prophet R package inside of Docker container:
# https://github.com/alexeybutyrev/dockerprophet

FROM rocker/rstudio:4.2.1
#FROM rocker/r-base
## Using a base image with R4.2.1 and RSTUDIO_VERSION=2022.07.2+576
WORKDIR /code/data-processing

## Check for updates
RUN apt-get update && apt-get install -y \
    sudo \
    gdebi-core \
    libcairo2-dev \
    libxt-dev \
    libcurl4-openssl-dev libssl-dev \
    r-cran-rstan


## Explicitly setting my default RStudio Package Manager Repo
## Uses packages as at 24/12/2022
RUN echo "r <- getOption('repos'); \
	  r['CRAN'] <- 'https://packagemanager.rstudio.com/cran/__linux__/focal/2021-12-24'; \
	  options(repos = r);" > ~/.Rprofile



RUN install2.r \
    --skipinstalled \
    httr \
    data.table \
    dplyr \
    tidyr \
    lubridate \
    ggplot2 \
    stringr \
    fastDummies \
    zoo \
    forecast \
    -e prophet


CMD ["Rscript", "/code/data-processing/stata_erwarteter_stromverbrauch/Stromverbrauch_OGD.R"]

# Docker commands to create image and run container:
# cd stata_erwateter_stromverbrauch
# docker build -t stromverbrauch .
# cd ..
# docker run -it --rm -v /data/dev/workspace/data-processing:/code/data-processing -v /mnt/OGD-DataExch/StatA/Stromverbrauch:/code/data-processing/stata_erwarteter_stromverbrauch/data/export --name stromverbrauch stromverbrauch