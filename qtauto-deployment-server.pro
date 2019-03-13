TEMPLATE = aux

build_online_docs: {
    QMAKE_DOCS = $$PWD/doc/online/qtautodeploymentserver.qdocconf
} else {
    QMAKE_DOCS = $$PWD/doc/qtautodeploymentserver.qdocconf
}

OTHER_FILES += \
    $$PWD/doc/*.qdocconf \
    $$PWD/doc/src/*.qdoc

load(qt_docs)
