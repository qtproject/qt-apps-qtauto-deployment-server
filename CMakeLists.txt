# Copyright (C) 2023 The Qt Company Ltd.
# SPDX-License-Identifier: BSD-3-Clause

cmake_minimum_required(VERSION 3.16)

include(.cmake.conf)
project(QtAutoDeploymentServer
    VERSION "${QT_REPO_MODULE_VERSION}"
    DESCRIPTION "QtAuto deployment server"
    HOMEPAGE_URL "https://qt.io/"
    LANGUAGES CXX C
)

find_package(Qt6 ${PROJECT_VERSION} CONFIG REQUIRED COMPONENTS BuildInternals Core Network)

add_custom_target(create_docker
    COMMAND docker build -t qtauto-deployment-server .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    VERBATIM
)

qt_build_repo()


if(QT_BUILD_ONLINE_DOCS)
    set(DOC_CONF "doc/online/qtautodeploymentserver.qdocconf")
else()
    set(DOC_CONF "doc/qtautodeploymentserver.qdocconf")
endif()

file(GLOB_RECURSE allDocFiles "doc/*.qdoc" "doc/*.png" "doc/*.qdocconf")
add_custom_target(Documentation SOURCES ${allDocFiles})
qt_internal_add_docs(Documentation ${DOC_CONF})

# Add tool dependencies that were deferred by qt_internal_add_docs.
qt_internal_add_deferred_dependencies()
