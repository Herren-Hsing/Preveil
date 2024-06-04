#!/bin/bash

# Update package lists
sudo apt-get update

# Install GCC and Clang
sudo apt-get install -y gcc clang

# Install CMake
CMAKE_VERSION=3.15.0
if ! cmake --version | grep -q "$CMAKE_VERSION"; then
    sudo apt-get remove -y cmake
    wget https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION.tar.gz
    tar -zxvf cmake-$CMAKE_VERSION.tar.gz
    cd cmake-$CMAKE_VERSION
    ./bootstrap
    make
    sudo make install
    cd ..
    rm -rf cmake-$CMAKE_VERSION cmake-$CMAKE_VERSION.tar.gz
fi

# Install Boost
BOOST_VERSION=1.81.0
if ! dpkg -s libboost-dev | grep -q "$BOOST_VERSION"; then
    wget https://boostorg.jfrog.io/artifactory/main/release/$BOOST_VERSION/source/boost_${BOOST_VERSION//./_}.tar.gz
    tar -zxvf boost_${BOOST_VERSION//./_}.tar.gz
    cd boost_${BOOST_VERSION//./_}
    ./bootstrap.sh
    ./b2
    sudo ./b2 install
    cd ..
    rm -rf boost_${BOOST_VERSION//./_} boost_${BOOST_VERSION//./_}.tar.gz
fi

# Install GMP
sudo apt-get install -y libgmp-dev

# Install libsodium
sudo apt-get install -y libsodium-dev

# Install OpenSSL
sudo apt-get install -y libssl-dev

# Install NTL (optional)
sudo apt-get install -y libntl-dev

# Install Python 3 and pip
sudo apt-get install -y python3 python3-pip

# Install Python packages
pip3 install -r requirements.txt

echo "All required packages have been installed."
