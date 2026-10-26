"""Bind library-specific discovery to the artifact dependencies in the request."""

from dataclasses import replace
import shlex
from forgedeps.environments import build_cmake


def _bound(ctx, bindings):
    options = list(ctx.options.get("cmake_options", ()))
    for variable, name in bindings:
        if name not in ctx.requires:
            raise ValueError("The shared recipe requires an artifact: " + name)
        options = [option for option in options if not option.startswith("-D" + variable + "=")]
        options.append("-D" + variable + "=" + str(ctx.requires[name].prefix))
    return replace(ctx, options={**ctx.options, "cmake_options": options})


def build_ngtcp2(ctx):
    build_cmake(_bound(ctx, (("OPENSSL_ROOT_DIR", "openssl"),)))


def _static(prefix, name, windows):
    names = (f'{name}_static.lib', f'lib{name}_static.a', f'lib{name}.a') if windows else (f'lib{name}.a',)
    for filename in names:
        candidate = prefix / 'lib' / filename
        if candidate.is_file():
            return candidate
    raise ValueError('Missing static protocol library in its artifact: ' + name)


def build_curl(ctx):
    bindings = [('ZLIB_ROOT', 'zlib')]
    if 'openssl' in ctx.requires:
        bindings.append(('OPENSSL_ROOT_DIR', 'openssl'))
    ctx = _bound(ctx, bindings)
    options = list(ctx.options.get('cmake_options', ()))
    windows = ctx.target.get('platform') == 'Windows'
    if 'ngtcp2' in ctx.requires or 'nghttp2' in ctx.requires:
        # curl's raw protocol libraries must come from the same artifact graph.
        options += ['-DCURL_USE_PKGCONFIG=OFF']
        for variable, library, dependency in (
                ('NGTCP2_LIBRARY', 'ngtcp2', 'ngtcp2'),
                ('NGTCP2_CRYPTO_OSSL_LIBRARY', 'ngtcp2_crypto_ossl', 'ngtcp2'),
                ('NGHTTP3_LIBRARY', 'nghttp3', 'nghttp3'),
                ('NGHTTP2_LIBRARY', 'nghttp2', 'nghttp2')):
            if dependency in ctx.requires:
                prefix = ctx.requires[dependency].prefix
                options += [f'-D{variable}={_static(prefix, library, windows).as_posix()}',
                            f'-D{dependency.upper()}_INCLUDE_DIR={(prefix / "include").as_posix()}']
        if windows:
            # Preserve the caller's compiler flags, then request static headers.
            flags = next((item.split('=', 1)[1] for item in reversed(options)
                          if item.startswith('-DCMAKE_C_FLAGS=')), '')
            options += ['-DCURL_USE_SCHANNEL=OFF', '-DCMAKE_C_FLAGS=' + flags +
                        ' -DNGTCP2_STATICLIB -DNGHTTP3_STATICLIB -DNGHTTP2_STATICLIB']
        elif ctx.target.get('platform') == 'Linux' and 'ngtcp2' in ctx.requires:
            prefix = ctx.requires['openssl'].prefix
            tail = ' '.join(shlex.quote(str(prefix / 'lib' / name)) for name in ('libssl.a', 'libcrypto.a'))
            previous = next((item.split('=', 1)[1] for item in reversed(options)
                             if item.startswith('-DCMAKE_C_STANDARD_LIBRARIES=')), '')
            options += ['-DCMAKE_C_STANDARD_LIBRARIES=' + previous + ' ' + tail + ' -ldl -pthread']
    build_cmake(replace(ctx, options={**ctx.options, 'cmake_options': options}))
