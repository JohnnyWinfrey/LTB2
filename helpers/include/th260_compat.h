// th260_compat.h -- makes th260_helper_ultra.cpp buildable both ways.
//
// 1. Windows target: if the real PicoQuant SDK headers are sitting next to this
//    file (th260lib.h / th260defin.h / errorcodes.h, copied off the instrument
//    PC), they are used verbatim -- their declarations are authoritative.
// 2. Native macOS/Linux target: the SDK headers do not exist and could not be
//    used anyway, so this file declares the subset of the TH260 API the helper
//    actually calls. helpers/th260_stub.cpp supplies the bodies, which lets the
//    same helper source be built and exercised locally.
//
// The __has_include guard means dropping the real headers into helpers/include/
// silently switches case 2 off. Nothing else has to change.

#ifndef TH260_COMPAT_H
#define TH260_COMPAT_H

#if defined(__has_include)
#  if __has_include("th260lib.h")
#    define TH260_HAVE_SDK_HEADERS 1
#  endif
#endif

#ifdef TH260_HAVE_SDK_HEADERS

// th260lib.h spells the calling convention MSVC's way (_stdcall) and only
// defines it away when _WIN32 is undefined -- which leaves GCC/mingw stuck on
// a Windows target, since GCC spells it __stdcall. Define it here first; the
// header's own guard then reduces to a benign identical redefinition.
// x64 has a single calling convention, so empty is correct there.
#if defined(__GNUC__) && !defined(_stdcall)
#  if defined(_WIN32) && !defined(_WIN64)
#    define _stdcall __stdcall
#  else
#    define _stdcall
#  endif
#endif

extern "C" {
#include <errorcodes.h>
#include <th260defin.h>
#include <th260lib.h>
}

#else  // ---------------------------------------------------------------------

// Constants from th260defin.h.
#define MAXDEVNUM     4
#define MAXINPCHAN    2
#define MAXHISTLEN    32768
#define MAXLENCODE    5
#define MODE_HIST     0
#define FLAG_OVERFLOW 0x0001

// The TH260 library is __stdcall on 32-bit Windows; x64 has a single calling
// convention and non-Windows targets have no such attribute at all.
#if defined(_WIN32) && !defined(_WIN64)
#  define TH260_API __stdcall
#else
#  define TH260_API
#endif

extern "C" {

int TH260_API TH260_GetErrorString(char* errstring, int errcode);

int TH260_API TH260_OpenDevice(int devidx, char* serial);
int TH260_API TH260_CloseDevice(int devidx);
int TH260_API TH260_Initialize(int devidx, int mode);

int TH260_API TH260_GetHardwareInfo(int devidx, char* model, char* partno, char* version);
int TH260_API TH260_GetNumOfInputChannels(int devidx, int* nchannels);
int TH260_API TH260_GetResolution(int devidx, double* resolution);

int TH260_API TH260_SetSyncDiv(int devidx, int divider);
int TH260_API TH260_SetSyncCFD(int devidx, int level, int zerocross);
int TH260_API TH260_SetSyncEdgeTrg(int devidx, int level, int edge);
int TH260_API TH260_SetSyncChannelOffset(int devidx, int value);

int TH260_API TH260_SetInputCFD(int devidx, int channel, int level, int zerocross);
int TH260_API TH260_SetInputEdgeTrg(int devidx, int channel, int level, int edge);
int TH260_API TH260_SetInputChannelOffset(int devidx, int channel, int value);

int TH260_API TH260_SetHistoLen(int devidx, int lencode, int* actuallen);
int TH260_API TH260_SetBinning(int devidx, int binning);
int TH260_API TH260_SetOffset(int devidx, int offset);
int TH260_API TH260_SetStopOverflow(int devidx, int stop_ovfl, unsigned int stopcount);

int TH260_API TH260_ClearHistMem(int devidx);
int TH260_API TH260_StartMeas(int devidx, int tacq);
int TH260_API TH260_StopMeas(int devidx);
int TH260_API TH260_CTCStatus(int devidx, int* ctcstatus);
int TH260_API TH260_GetHistogram(int devidx, unsigned int* chcount, int channel, int clear);

int TH260_API TH260_GetSyncRate(int devidx, int* syncrate);
int TH260_API TH260_GetCountRate(int devidx, int channel, int* cntrate);
int TH260_API TH260_GetFlags(int devidx, int* flags);
int TH260_API TH260_GetWarnings(int devidx, int* warnings);
int TH260_API TH260_GetWarningsText(int devidx, char* text, int warnings);

}  // extern "C"

#endif  // TH260_HAVE_SDK_HEADERS

#endif  // TH260_COMPAT_H
