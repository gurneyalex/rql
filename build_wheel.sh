#!/bin/sh

set -ex

mkdir -p dist
if ! test -e /.dockerenv; then
  exec docker run --rm -it -v $(pwd):/mnt/host/rql quay.io/pypa/manylinux1_x86_64 sh /mnt/host/rql/$0
fi

cd /mnt/host
VERSION=4.4.0
curl -L https://github.com/Gecode/gecode/archive/release-$VERSION.tar.gz | tar -xzf -
cd gecode-release-$VERSION
./configure
make -j2
make install

mkdir -p /wheelhouse
# Compile wheels
for PYBIN in /opt/python/*/bin; do
    "${PYBIN}/pip" wheel /mnt/host/rql -w /wheelhouse
done

# Bundle external shared libraries into the wheels
for whl in /wheelhouse/rql*.whl; do
    auditwheel repair "$whl" -w /wheelhouse
done

# Install packages and test
for PYBIN in /opt/python/*/bin/; do
    "${PYBIN}/pip" install pytest
    "${PYBIN}/pip" install rql --no-index -f /wheelhouse
    "${PYBIN}/python" -c 'import sys; assert sys.version_info[:2] == (2, 7)' && "${PYBIN}/pip" install unittest2
    echo "************  test on $PYBIN"
    (cd "/mnt/host"; "${PYBIN}/py.test" rql)
done
mv /wheelhouse/rql*manylinux*.whl /mnt/host/rql/dist/

