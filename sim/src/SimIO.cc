#include "SimIO.hh"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <sys/types.h>

namespace SimIO {
namespace {

using BinaryPrimaryRow = SimStructures::detail::BinaryPrimaryRow;
using BinarySecondaryRow = SimStructures::detail::BinarySecondaryRow;
using BinaryPhotonRow = SimStructures::detail::BinaryPhotonRow;
constexpr std::size_t kSpeciesLabelSize = SimStructures::detail::kSpeciesLabelSize;

enum class BinaryOutputKind {
  Primaries,
  Secondaries,
  Photons,
};

// Persistent file handles kept open per worker thread.
struct BinaryFileState {
  FILE* primariesFile = nullptr;
  FILE* secondariesFile = nullptr;
  FILE* photonsFile = nullptr;
  std::string primariesPath;
  std::string secondariesPath;
  std::string photonsPath;
};

struct BinaryFileLocks {
  std::mutex primaries;
  std::mutex secondaries;
  std::mutex photons;
};

// Thread-local state to avoid file handle conflicts
thread_local BinaryFileState g_binaryState;
BinaryFileLocks g_binaryLocks;

// Binary file header (64 bytes, fixed size for easy parsing)
struct BinaryHeader {
  char magic[8];            // "SCINPIX\0"
  std::uint32_t version;    // Format version (1)
  std::uint32_t recordSize; // Size of each record in bytes
  std::uint64_t recordCount; // Number of records written (informational)
  char padding[40];         // Reserved for future use
};

bool EnsureParentDirectory(const std::string& filePath) {
  // Find last directory separator
  std::size_t lastSlash = filePath.find_last_of("/\\");
  if (lastSlash == std::string::npos) {
    return true; // No directory component
  }

  std::string parentPath = filePath.substr(0, lastSlash);
  if (parentPath.empty()) {
    return true;
  }

  // Check if directory exists using POSIX stat
  struct stat info;
  if (stat(parentPath.c_str(), &info) != 0) {
    return false; // Doesn't exist or can't access
  }
  return (info.st_mode & S_IFDIR) != 0; // Check if it's a directory
}

void CopyLabel(const std::string& in, char out[kSpeciesLabelSize]) {
  std::memset(out, 0, kSpeciesLabelSize);
  std::strncpy(out, in.c_str(), kSpeciesLabelSize - 1);
}

std::vector<BinaryPrimaryRow> ToNative(const std::vector<PrimaryInfo>& rows) {
  std::vector<BinaryPrimaryRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    BinaryPrimaryRow native{};
    native.gun_call_id = row.gunCallId;
    native.primary_track_id = row.primaryTrackId;
    CopyLabel(row.primarySpecies, native.primary_species);
    native.primary_x_mm = row.primaryXmm;
    native.primary_y_mm = row.primaryYmm;
    native.primary_energy_MeV = row.primaryEnergyMeV;
    native.primary_interaction_time_ns = row.primaryInteractionTimeNs;
    native.primary_created_secondary_count = row.primaryCreatedSecondaryCount;
    native.primary_generated_optical_photon_count =
        row.primaryGeneratedOpticalPhotonCount;
    native.primary_detected_optical_interface_photon_count =
        row.primaryDetectedOpticalInterfacePhotonCount;
    out.push_back(native);
  }
  return out;
}

std::vector<BinarySecondaryRow> ToNative(const std::vector<SecondaryInfo>& rows) {
  std::vector<BinarySecondaryRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    BinarySecondaryRow native{};
    native.gun_call_id = row.gunCallId;
    native.primary_track_id = row.primaryTrackId;
    native.secondary_track_id = row.secondaryTrackId;
    CopyLabel(row.secondarySpecies, native.secondary_species);
    native.secondary_origin_x_mm = row.secondaryOriginXmm;
    native.secondary_origin_y_mm = row.secondaryOriginYmm;
    native.secondary_origin_z_mm = row.secondaryOriginZmm;
    native.secondary_origin_energy_MeV = row.secondaryOriginEnergyMeV;
    native.secondary_end_x_mm = row.secondaryEndXmm;
    native.secondary_end_y_mm = row.secondaryEndYmm;
    native.secondary_end_z_mm = row.secondaryEndZmm;
    out.push_back(native);
  }
  return out;
}

std::vector<BinaryPhotonRow> ToNative(const std::vector<PhotonInfo>& rows) {
  std::vector<BinaryPhotonRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    BinaryPhotonRow native{};
    native.gun_call_id = row.gunCallId;
    native.primary_track_id = row.primaryTrackId;
    native.secondary_track_id = row.secondaryTrackId;
    native.photon_track_id = row.photonTrackId;
    native.photon_creation_time_ns = row.photonCreationTimeNs;
    native.photon_origin_x_mm = row.photonOriginXmm;
    native.photon_origin_y_mm = row.photonOriginYmm;
    native.photon_origin_z_mm = row.photonOriginZmm;
    native.photon_scint_exit_x_mm = row.photonScintExitXmm;
    native.photon_scint_exit_y_mm = row.photonScintExitYmm;
    native.photon_scint_exit_z_mm = row.photonScintExitZmm;
    native.optical_interface_hit_x_mm = row.opticalInterfaceHitXmm;
    native.optical_interface_hit_y_mm = row.opticalInterfaceHitYmm;
    native.optical_interface_hit_time_ns = row.opticalInterfaceHitTimeNs;
    native.optical_interface_hit_dir_x = row.opticalInterfaceHitDirX;
    native.optical_interface_hit_dir_y = row.opticalInterfaceHitDirY;
    native.optical_interface_hit_dir_z = row.opticalInterfaceHitDirZ;
    native.optical_interface_hit_pol_x = row.opticalInterfaceHitPolX;
    native.optical_interface_hit_pol_y = row.opticalInterfaceHitPolY;
    native.optical_interface_hit_pol_z = row.opticalInterfaceHitPolZ;
    native.optical_interface_hit_energy_eV = row.opticalInterfaceHitEnergyEV;
    native.optical_interface_hit_wavelength_nm = row.opticalInterfaceHitWavelengthNm;
    out.push_back(native);
  }
  return out;
}

bool WriteBinaryHeader(FILE* f, std::uint32_t recordSize) {
  BinaryHeader header{};
  std::memcpy(header.magic, "SCINPIX", 8);
  header.version = 1;
  header.recordSize = recordSize;
  header.recordCount = 0; // Will be updated by reader if needed

  return (std::fwrite(&header, sizeof(header), 1, f) == 1);
}

FILE** FileSlot(BinaryFileState& state, BinaryOutputKind kind) {
  switch (kind) {
    case BinaryOutputKind::Primaries:
      return &state.primariesFile;
    case BinaryOutputKind::Secondaries:
      return &state.secondariesFile;
    case BinaryOutputKind::Photons:
      return &state.photonsFile;
  }
  return nullptr;
}

std::string* PathSlot(BinaryFileState& state, BinaryOutputKind kind) {
  switch (kind) {
    case BinaryOutputKind::Primaries:
      return &state.primariesPath;
    case BinaryOutputKind::Secondaries:
      return &state.secondariesPath;
    case BinaryOutputKind::Photons:
      return &state.photonsPath;
  }
  return nullptr;
}

std::mutex& FileMutex(BinaryOutputKind kind) {
  switch (kind) {
    case BinaryOutputKind::Primaries:
      return g_binaryLocks.primaries;
    case BinaryOutputKind::Secondaries:
      return g_binaryLocks.secondaries;
    case BinaryOutputKind::Photons:
      return g_binaryLocks.photons;
  }
  return g_binaryLocks.photons;
}

bool FileExists(const std::string& path) {
  FILE* f = std::fopen(path.c_str(), "rb");
  if (!f) {
    return false;
  }
  std::fclose(f);
  return true;
}

bool CreateBinaryFile(const std::string& path, std::uint32_t recordSize) {
  FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) {
    return false;
  }

  const bool success = WriteBinaryHeader(f, recordSize);
  std::fclose(f);
  return success;
}

FILE* EnsureFileOpen(BinaryOutputKind kind,
                     const std::string& path,
                     std::uint32_t recordSize) {
  auto& state = g_binaryState;
  FILE** filePtr = FileSlot(state, kind);
  std::string* pathPtr = PathSlot(state, kind);

  // If file is already open for this path, return it
  if (*filePtr && *pathPtr == path) {
    return *filePtr;
  }

  // Close old file if path changed
  if (*filePtr) {
    std::fclose(*filePtr);
    *filePtr = nullptr;
  }

  if (!FileExists(path) && !CreateBinaryFile(path, recordSize)) {
    return nullptr;
  }

  *filePtr = std::fopen(path.c_str(), "ab");
  if (!*filePtr) {
    return nullptr;
  }

  *pathPtr = path;
  return *filePtr;
}

template<typename T>
bool AppendBinaryRecords(BinaryOutputKind kind,
                         const std::string& path,
                         const std::vector<T>& rows) {
  if (rows.empty()) {
    return true;
  }

  std::lock_guard<std::mutex> lock(FileMutex(kind));
  FILE* f = EnsureFileOpen(kind, path, sizeof(T));
  if (!f) {
    return false;
  }

  bool success = (std::fwrite(rows.data(), sizeof(T), rows.size(), f) == rows.size());
  success = success && (std::fflush(f) == 0);
  return success;
}

}  // namespace

bool InitOutput(const OutputPaths& paths,
                const OutputSelection& selection,
                std::string* errorMessage) {
  if (selection.primaries && !EnsureParentDirectory(paths.primaries)) {
    if (errorMessage) {
      *errorMessage = "Output directory does not exist for " + paths.primaries;
    }
    return false;
  }

  if (selection.secondaries && !EnsureParentDirectory(paths.secondaries)) {
    if (errorMessage) {
      *errorMessage = "Output directory does not exist for " + paths.secondaries;
    }
    return false;
  }

  if (selection.photons && !EnsureParentDirectory(paths.photons)) {
    if (errorMessage) {
      *errorMessage = "Output directory does not exist for " + paths.photons;
    }
    return false;
  }

  if (selection.primaries &&
      !CreateBinaryFile(paths.primaries, sizeof(BinaryPrimaryRow))) {
    if (errorMessage) {
      *errorMessage = "Failed to initialize primary output " + paths.primaries;
    }
    return false;
  }

  if (selection.secondaries &&
      !CreateBinaryFile(paths.secondaries, sizeof(BinarySecondaryRow))) {
    if (errorMessage) {
      *errorMessage = "Failed to initialize secondary output " + paths.secondaries;
    }
    return false;
  }

  if (selection.photons &&
      !CreateBinaryFile(paths.photons, sizeof(BinaryPhotonRow))) {
    if (errorMessage) {
      *errorMessage = "Failed to initialize photon output " + paths.photons;
    }
    return false;
  }

  return true;
}

bool AppendOutput(const OutputPaths& paths,
                  const OutputSelection& selection,
                  const std::vector<PrimaryInfo>& primaryRows,
                  const std::vector<SecondaryInfo>& secondaryRows,
                  const std::vector<PhotonInfo>& photonRows,
                  std::string* errorMessage) {
  if (selection.primaries && !primaryRows.empty()) {
    auto primaryNative = ToNative(primaryRows);
    if (!AppendBinaryRecords(BinaryOutputKind::Primaries,
                             paths.primaries,
                             primaryNative)) {
      if (errorMessage) {
        *errorMessage = "Failed to append primary records to " + paths.primaries;
      }
      return false;
    }
  }

  if (selection.secondaries && !secondaryRows.empty()) {
    auto secondaryNative = ToNative(secondaryRows);
    if (!AppendBinaryRecords(BinaryOutputKind::Secondaries,
                             paths.secondaries,
                             secondaryNative)) {
      if (errorMessage) {
        *errorMessage = "Failed to append secondary records to " + paths.secondaries;
      }
      return false;
    }
  }

  if (selection.photons && !photonRows.empty()) {
    auto photonNative = ToNative(photonRows);
    if (!AppendBinaryRecords(BinaryOutputKind::Photons,
                             paths.photons,
                             photonNative)) {
      if (errorMessage) {
        *errorMessage = "Failed to append photon records to " + paths.photons;
      }
      return false;
    }
  }

  return true;
}

void CloseOutput(const std::string& /*outputPath*/) {
  auto& state = g_binaryState;

  if (state.primariesFile) {
    std::fclose(state.primariesFile);
    state.primariesFile = nullptr;
  }
  if (state.secondariesFile) {
    std::fclose(state.secondariesFile);
    state.secondariesFile = nullptr;
  }
  if (state.photonsFile) {
    std::fclose(state.photonsFile);
    state.photonsFile = nullptr;
  }

  state.primariesPath.clear();
  state.secondariesPath.clear();
  state.photonsPath.clear();
}

}  // namespace SimIO
