# Preveil
In the era of big data, ensuring secure data sharing has become a crucial technical challenge in data-driven applications. To overcome the reliance on central trusted servers in traditional privacy protection techniques, this project employs a combination of secure multi-party computation (MPC) and differential privacy. This approach leverages a distributed platform to execute data synthesis tasks. Throughout the entire data sharing process, only the data providers hold the original datasets, and the MPC aggregator or server cannot access the plaintext information directly. This significantly reduces the risk of data breaches. The datasets published after being synthesized by the server retain the distribution characteristics and statistical properties of the original data while effectively protecting the privacy of the original datasets, ensuring high data utility. 

## Environment Setup:

#### MP-SPDZ
##### Installing Packages
Use the following command to install the required packages:

```
sudo apt-get install automake build-essential clang cmake git libboost-dev libboost-thread-dev libgmp-dev libntl-dev libsodium-dev libssl-dev libtool python3
```

Download `mp-spdz-0.3.8.tar.xz` from this [link](https://github.com/data61/MP-SPDZ/releases) and extract it. Then, in the extracted folder, execute the following commands to check if the files in `mp-spdz-0.3.8.tar.xz` are working properly:

```
Scripts/tldr.sh
echo 1 2 3 4 > Player-Data/Input-P0-0
echo 1 2 3 4 > Player-Data/Input-P1-0
Scripts/compile-run.py -E mascot tutorial
```

```
make -j8 mascot-party.x
make setup
echo 1 2 3 4 > Player-Data/Input-P0-0
echo 1 2 3 4 > Player-Data/Input-P1-0
Scripts/compile-run.py -E mascot tutorial
```

Follow [Tutorial 1](https://blog.csdn.net/G_1012_/article/details/129730072) and [Tutorial 2](https://blog.csdn.net/ghostyusheng/article/details/80321483) to install Docker.

After successful installation, go to the MP-SPDZ folder and use the following commands to build and run a Docker image for `mascot-party.x`:

```
docker build --tag mpspdz:mascot-party --build-arg machine=mascot-party.x .
```

```
docker run --rm -it mpspdz:mascot-party ./Scripts/mascot.sh tutorial
```

Ensure the following Ubuntu packages meet the requirements. If they do not, make the necessary changes:

- GCC 5 or higher (tested up to 11) or LLVM/clang 6 or higher (tested up to 14). The default is to use clang as it performs better. Note that GCC 5/6 and clang 9 do not support libOTe, so you need to avoid using these compilers.
- For protocols using oblivious transfer, libOTe with the necessary patches from [this link](https://github.com/mkskeller/softspoken-implementation), but without SimplestOT. The easiest way is to run `make libot`, which will install it in a subdirectory if needed. libOTe requires CMake version 3.15 or higher, which is not available by default on older systems like Ubuntu 18.04. You can run `make cmake` to install it locally.
- libOTe also requires Boost version 1.75 or higher, which is not available by default on relatively new systems like Ubuntu 22.04. You can install it locally by running `make boost`.
- GMP library, supporting C++ compilation (use the '--enable-cxx' flag) when running configure. Tested with version 6.2.1 on Ubuntu.
- libsodium, minimum version 1.0.18
- OpenSSL, minimum version 3.0.2
- libboost-dev, minimum version 1.81
- libboost-thread-dev, minimum version 1.81
- x86 or ARM 64-bit CPU
- Python 3.5 or higher
- NTL library for homomorphic encryption (optional, minimum version 11.5.1 if chosen)

##### Generating Certificates and Keys

MP-SPDZ will use OpenSSL as a secure channel. Use the following command to generate the necessary certificates and keys:

`Scripts/setup-ssl.sh [<number of parties> <ssl_dir>]`

The program requires keys and certificates in `SSL_DIR/P<i>.key` and `SSL_DIR/P<i>.pem`, with certificates using the common name `P<i>` for party `<i>`. Additionally, related root certificates must be in the `SSL_DIR` directory so OpenSSL can find them (run `c_rehash <ssl_dir>`). The above command will generate self-signed certificates. If running on different hosts, copy these certificates and keys. Note that `<ssl_dir>` must match the `SSL_DIR` setting in `CONFIG.mine`, with the default `<ssl_dir>` being `Player-Data`.

###### Running Computations

There are three ways to run computations:

1. Compile and run separately. This allows running the same program without recompiling each time.
   ```
   ./compile.py <program> <argument>
   Scripts/mascot.sh <program>-<argument> [<runtime-arg>...]
   Scripts/mascot.sh <program>-<argument> [<runtime-arg>...]
   ```
2. Single-command local execution. This will compile the program and virtual machine, then run it locally. The protocol name corresponds to the script name (without '.sh'). Additionally, some protocol-specific optimization options are automatically used along with the required options.
    ```
   Scripts/compile-run.py -E mascot <program> <argument> -- [<runtime-arg>...]
   ```
3. Single-command remote execution. This will compile the program and virtual machine if needed, then upload all necessary input and certificate files via SSH.
    ```
   Scripts/compile-run.py -H HOSTS -E mascot <program> <argument> -- [<runtime-arg>...]
   ```

   `HOSTS` must be a text file in the following format:
    ```
   [<user>@]<host0>[/<path>]
   [<user>@]<host1>[/<path>]
   ...
    ```
   If <path> does not start with '/', it is relative to the user's home directory. If it starts with '//' after the hostname, it is relative to the root directory.

The following example uses the Ring protocol to demonstrate usage; other protocols work similarly.

First, compile the virtual machine:

`make -j 8 replicated-ring-party.x`

To run with three parties on one machine, execute:

`./replicated-ring-party.x -I 0 tutorial`

`./replicated-ring-party.x -I 1 tutorial` (in a separate terminal)

`./replicated-ring-party.x -I 2 tutorial` (in a separate terminal)

Alternatively, use the script to run two parties automatically in non-interactive mode:

`Scripts/ring.sh tutorial`

The default TCP port number is 5000, which can be changed with the `-pn` option.

#### private-pgm
Install Python 3, then execute the following command in the private-pgm directory:
```
$ pip install -r requirements.txt
```
Add the src folder to PYTHONPATH. In Ubuntu, add the following line to the .bashrc file:
```
PYTHONPATH=$PYTHONPATH:/path/to/private-pgm/src
```
Apply the changes with the following command:
```
$ source ~/.bashrc
```

After completing this, check to ensure the tests pass:
``` from mbi import FactoredInference ```
```
$ cd /path/to/private-pgm/test
$ nosetests
........................................
----------------------------------------------------------------------
Ran 40 tests in 5.009s

OK
```

## Import Database

Ensure the necessary database management system (e.g., MySQL, PostgreSQL) is installed, then import the SQL files from the `database` directory to create the database tables.

## Run Executable

1. Ensure the executable file is in the same directory as the source files.
2. Run the executable file.
