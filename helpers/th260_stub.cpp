// th260_stub.cpp -- synthetic stand-in for th260lib64.dll.
//
// Links against th260_helper_ultra.cpp in place of the real PicoQuant library
// so the helper can be built and driven natively on a machine with no TimeHarp
// (and no Windows). It exercises the actual helper code -- the command parser,
// the response formatter, the stdout/stderr split -- against a fake board that
// reports two channels and returns a single-exponential decay.
//
// Only reachable via helpers/build.sh stub; the Windows build never sees it.

#include <cmath>
#include <cstring>
#include <random>
#include <string>

#include "th260_compat.h"

namespace {

const int kHistLen = 32768;
const double kResolutionPs = 200.0;  // Binning = 3 => 0.2 ns
const int kNumChannels = 2;

bool opened = false;
int tacqMs = 0;

std::mt19937& rng() {
    static std::mt19937 gen(12345);  // fixed seed: stub runs are reproducible
    return gen;
}

}  // namespace

extern "C" {

int TH260_GetErrorString(char* errstring, int errcode) {
    std::snprintf(errstring, 40, "stub_error_%d", errcode);
    return 0;
}

int TH260_OpenDevice(int devidx, char* serial) {
    if (devidx != 0) return -1;  // only device 0 exists
    std::strcpy(serial, "STUB01");
    opened = true;
    return 0;
}

int TH260_CloseDevice(int) { opened = false; return 0; }
int TH260_Initialize(int, int) { return opened ? 0 : -1; }

int TH260_GetHardwareInfo(int, char* model, char* partno, char* version) {
    std::strcpy(model, "TimeHarp 260 P");
    std::strcpy(partno, "930043");
    std::strcpy(version, "1.0");
    return 0;
}

int TH260_GetNumOfInputChannels(int, int* n) { *n = kNumChannels; return 0; }
int TH260_GetResolution(int, double* r) { *r = kResolutionPs; return 0; }

int TH260_SetSyncDiv(int, int) { return 0; }
int TH260_SetSyncCFD(int, int, int) { return 0; }
int TH260_SetSyncEdgeTrg(int, int, int) { return 0; }
int TH260_SetSyncChannelOffset(int, int) { return 0; }
int TH260_SetInputCFD(int, int, int, int) { return 0; }
int TH260_SetInputEdgeTrg(int, int, int, int) { return 0; }
int TH260_SetInputChannelOffset(int, int, int) { return 0; }

int TH260_SetHistoLen(int, int, int* actuallen) { *actuallen = kHistLen; return 0; }
int TH260_SetBinning(int, int) { return 0; }
int TH260_SetOffset(int, int) { return 0; }
int TH260_SetStopOverflow(int, int, unsigned int) { return 0; }

int TH260_ClearHistMem(int) { return 0; }
int TH260_StartMeas(int, int tacq) { tacqMs = tacq; return 0; }
int TH260_StopMeas(int) { return 0; }
int TH260_CTCStatus(int, int* status) { *status = 1; return 0; }  // finishes immediately

// Rising edge into a single-exponential decay, Poisson-sampled. Channel 1 gets
// a longer lifetime than channel 0 so the two are distinguishable downstream.
int TH260_GetHistogram(int, unsigned int* chcount, int channel, int) {
    const double peak = 1.0e4 * (tacqMs / 5000.0 > 0 ? tacqMs / 5000.0 : 1.0);
    const double tauBins = (channel == 0 ? 12.0 : 20.0) / (kResolutionPs / 1000.0);
    const double riseBins = 3.0;
    const int t0 = 40;

    for (int j = 0; j < kHistLen; j++) {
        double mean = 2.0;  // dark counts
        if (j >= t0) {
            const double dt = j - t0;
            mean += peak * (1.0 - std::exp(-dt / riseBins)) * std::exp(-dt / tauBins);
        }
        std::poisson_distribution<int> pois(mean);
        chcount[j] = static_cast<unsigned int>(pois(rng()));
    }
    return 0;
}

int TH260_GetSyncRate(int, int* syncrate) { *syncrate = 40000000; return 0; }
int TH260_GetCountRate(int, int channel, int* cntrate) { *cntrate = 25000 + channel * 1000; return 0; }
int TH260_GetFlags(int, int* flags) { *flags = 0; return 0; }
int TH260_GetWarnings(int, int* warnings) { *warnings = 0; return 0; }
int TH260_GetWarningsText(int, char* text, int) { text[0] = '\0'; return 0; }

}  // extern "C"
