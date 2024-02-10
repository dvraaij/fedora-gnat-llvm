# OPEN-ISSUE: Can we switch toolchain flags during the build? See also:
# https://docs.fedoraproject.org/en-US/packaging-guidelines/#_compiler_macros

# OPEN-ISSUE: Can't get the shared libraries to build. Error: "only static
# libraries are supported on this platform" (?).

# Constrain make to 1 CPU to see the log output.
%{constrain_build -c 1}

# Upstream source information.
%global upstream_owner        AdaCore
%global upstream_name         gnat-llvm
%global upstream_commit_date  20240201
%global upstream_commit       5d318d7a49f4523be1eb0be0ad6d0f4fe50a9c2f
%global upstream_shortcommit  %(c=%{upstream_commit}; echo ${c:0:7})

# Compatible major version of LLVM.
%global llvm_version 16

# Latest major version of LLVM available in Fedora.
%global llvm_latest  17

# GNAT-LLVM depends on a recent version of the GNAT source code.
%global gcc_version  14.0.1-20240208
%global gcc_sha512   02054b26fe0500d4ad88deeb41b5d356b70dafcc3fcb98c790d79e78f1c9a1d77654d2b553b43ab273147d9cfe76b801c2c9a1903caafce84bbffd5fb177c53d

Name:           gnat-llvm
Version:        0^%{upstream_commit_date}git%{upstream_shortcommit}
Release:        1%{?dist}
Summary:        An Ada compiler based on LLVM

License:        GPL-3.0-or-later

URL:            https://github.com/%{upstream_owner}/%{upstream_name}
Source0:        https://github.com/%{upstream_owner}/%{upstream_name}/archive/%{upstream_commit}.tar.gz#/%{name}-%{upstream_shortcommit}.tar.gz

# The compiler is build from the GNAT front-end source code.
Source1:        https://src.fedoraproject.org/repo/pkgs/gcc/gcc-%{gcc_version}.tar.xz/sha512/%{gcc_sha512}/gcc-%{gcc_version}.tar.xz


# [Fedora-specific] Older version of the LLVM tools have a postfix.
%if %{llvm_version} == 16
Patch:          %{name}-use-llvm16.patch
%endif
# [Fedora-specific] Link with libclang and libclang-cpp, not with libclangBasic.
Patch:          %{name}-link-with-clang-instead-of-clangBasic.patch
# [LLVM] Don't use `LLVMCreateTargetMachineWithABI` yet.
#    New API call will be available from LLVM 18 onwards.
#    See also: https://github.com/llvm/llvm-project/pull/68406
Patch:          %{name}-revert-270d0f.patch
Patch:          %{name}-revert-63b53f.patch

BuildRequires:  gcc-gnat gcc-c++ clang gprbuild make
# A fedora-gnat-project-common that contains GPRbuild_flags is needed.
BuildRequires:  fedora-gnat-project-common >= 3.17
%if %{llvm_version} == %{llvm_latest}
BuildRequires:  llvm-devel
BuildRequires:  clang-devel
%else
BuildRequires:  llvm%{llvm_version}-devel
BuildRequires:  clang%{llvm_version}-devel
%endif
BuildRequires:  libstdc++-static

%if %{llvm_version} == %{llvm_latest}
Requires:       llvm
%else
Requires:       llvm%{llvm_version}
%endif
Requires:       libgnat-llvm-static

# gnat-llvm is build from the GNAT source code. GNAT GCC itself is not
# included (as a binary) and can be installed alongside.
Provides:       bundled(gcc-gnat)

# Build only on architectures where GPRbuild is available.
# ExclusiveArch:  %{GPRbuild_arches}
ExclusiveArch:  x86_64 aarch64

%global common_description_en \
This is an Ada compiler based on LLVM, connecting the GNAT front-end to the \
LLVM code generator to generate LLVM bitcode for Ada and to open the LLVM \
ecosystem to Ada.

%description %{common_description_en}


#################
## Subpackages ##
#################

%package -n libgnat-llvm-devel
Summary:        GNAT-LLVM runtime systems.
License:        GPL-3.0-or-later WITH GCC-exception-3.1

%description -n libgnat-llvm-devel
This package includes the runtime systems (native and zero-footprint) for
GNAT-LLVM.


%package -n libgnat-llvm-static
Summary:        GNAT-LLVM runtime system static libraries
Requires:       libgnat-llvm-devel%{?_isa} = %{version}-%{release}
License:        GPL-3.0-or-later WITH GCC-exception-3.1

%description -n libgnat-llvm-static
This package includes static libraries, which are required to compile programs
compiled with the GNAT-LLVM.


%package tools
Summary:        Additional tools for use with the GNAT-LLVM compiler
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description tools
Additional tools for use with the GNAT-LLVM compiler.


#############
## Prepare ##
#############

%prep
%autosetup -n %{upstream_name}-%{upstream_commit} -p1

# Extract the GNAT sources from the GCC source tarball. Create a symbolic links
# that point to these GNAT sources.
tar --extract --xz --file %{SOURCE1} gcc-%{gcc_version}/gcc/ada
ln --symbolic ../gcc-%{gcc_version}         llvm-interface/gcc
ln --symbolic ../gcc-%{gcc_version}/gcc/ada llvm-interface/gnat_src


###########
## Build ##
###########

%build

# Disable LTO to prevent a "file-format not recognized" error during linking.
%global _lto_cflags %nil

# Disable PIE. GNAT-LLVM sets linker option '-no-pie' explicitly in
# llvm-interface/gnat_llvm.gpr. Not sure what will happen when you'd
# remove this option.
%undefine _hardened_build

# Build the compiler and tools.
%global toolchain gcc
%{make_build} -C llvm-interface build \
 GPRBUILD='gprbuild %{GPRbuild_flags}'

# Build the runtime systems (Native + ZFP).
%global toolchain clang
%{make_build} -C llvm-interface gnatlib-automated \
 GPRBUILD='gprbuild %{GPRbuild_flags}'
%{make_build} -C llvm-interface zfp-build \
 GPRBUILD='gprbuild %{GPRbuild_flags}'


#############
## Install ##
#############

%install

# Install the compiler.
gprinstall --create-missing-dirs --no-manifest \
           --prefix=%{buildroot}%{_prefix} --mode=usage \
           -P llvm-interface/gnat_llvm.gpr

# Install the tools.
gprinstall --create-missing-dirs --no-manifest \
           --prefix=%{buildroot}%{_prefix} --mode=usage \
           -P llvm-interface/tools.gpr

# Install the runtime systems.
function install_rts {
    mkdir --parents %{buildroot}%{_libdir}/libgnat-llvm/rts-$1
    cp --recursive --preserve=timestamps \
       llvm-interface/lib/rts-$1/{adainclude,adalib} \
       %{buildroot}%{_libdir}/libgnat-llvm/rts-$1
}

install_rts native
install_rts zfp

# Show installed files (to ease debugging based on build server logs).
find %{buildroot} -exec stat --format "%A %n" {} \;


###########
## Files ##
###########

%files
%license COPYING3
%doc README*
%{_bindir}/llvm-gnat
%{_bindir}/llvm-gnat1
%{_bindir}/llvm-gcc


%files -n libgnat-llvm-devel
%dir %{_libdir}/libgnat-llvm
# RTS Native
%dir %{_libdir}/libgnat-llvm/rts-native
%dir %{_libdir}/libgnat-llvm/rts-native/adalib
%{_libdir}/libgnat-llvm/rts-native/adainclude
%{_libdir}/libgnat-llvm/rts-native/adalib/*.ali
# RTS ZFP
%dir %{_libdir}/libgnat-llvm/rts-zfp
%dir %{_libdir}/libgnat-llvm/rts-zfp/adalib
%{_libdir}/libgnat-llvm/rts-zfp/adainclude
%{_libdir}/libgnat-llvm/rts-zfp/adalib/*.ali


%files -n libgnat-llvm-static
%{_libdir}/libgnat-llvm/rts-native/adalib/*.a
%{_libdir}/libgnat-llvm/rts-zfp/adalib/*.a


%files tools
%{_bindir}/llvm-gnatbind
%{_bindir}/llvm-gnatchop
%{_bindir}/llvm-gnatclean
%{_bindir}/llvm-gnatkr
%{_bindir}/llvm-gnatlink
%{_bindir}/llvm-gnatls
%{_bindir}/llvm-gnatmake
%{_bindir}/llvm-gnatname
%{_bindir}/llvm-gnatprep


###############
## Changelog ##
###############

%changelog
* Sun Feb 11 2024 Dennis van Raaij <dvraaij@fedoraproject.org> - 0^20240201git5d318d7-1
- Shapshot updated to: Git commit 5d318d7, 2024-02-01.

* Sun Aug 13 2023 Dennis van Raaij <dvraaij@fedoraproject.org> - 0^20230810git6f1fa83-1
- New package, snapshot: Git commit 6f1fa83, 2023-08-10.
