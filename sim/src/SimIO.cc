#include "SimIO.hh"

#include <hdf5.h>

#include <cstdint>
#include <cstring>
#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace SimIO {
namespace {

using Hdf5State = SimStructures::detail::Hdf5State;
using Hdf5PrimaryNativeRow = SimStructures::detail::Hdf5PrimaryNativeRow;
using Hdf5SecondaryNativeRow = SimStructures::detail::Hdf5SecondaryNativeRow;
using Hdf5PhotonNativeRow = SimStructures::detail::Hdf5PhotonNativeRow;
constexpr std::size_t kSpeciesLabelSize = SimStructures::detail::kHdf5SpeciesLabelSize;

// Global mutex to serialize HDF5 operations across threads
std::mutex g_hdf5Mutex;

// Thread-local state map - each thread gets its own file handles
// This is necessary because HDF5 file handles cannot be shared between threads
thread_local std::unordered_map<std::string, Hdf5State> tl_stateMap;

Hdf5State& GetState(const std::string& path) {
  return tl_stateMap[path];
}

void CloseState(Hdf5State& s) {
  if (s.dataset >= 0) {
    H5Dclose(s.dataset);
    s.dataset = -1;
  }
  if (s.datasetType >= 0) {
    H5Tclose(s.datasetType);
    s.datasetType = -1;
  }
  if (s.file >= 0) {
    H5Fclose(s.file);
    s.file = -1;
  }
  s.openPath.clear();
}

void CloseAll() {
  for (auto& [path, state] : tl_stateMap) {
    CloseState(state);
  }
  tl_stateMap.clear();
}

void CopyLabel(const std::string& in, char out[kSpeciesLabelSize]) {
  std::memset(out, 0, kSpeciesLabelSize);
  std::strncpy(out, in.c_str(), kSpeciesLabelSize - 1);
}

bool EnsureParentDirectory(const std::string& filePath) {
  const std::filesystem::path parent =
      std::filesystem::path(filePath).parent_path();
  if (parent.empty()) {
    return true;
  }

  std::error_code ec;
  return std::filesystem::exists(parent, ec) && !ec;
}

hid_t CreateFixedStringType(std::size_t size) {
  const hid_t t = H5Tcopy(H5T_C_S1);
  H5Tset_size(t, size);
  H5Tset_strpad(t, H5T_STR_NULLTERM);
  return t;
}

hid_t CreateExtendableDataset(hid_t file, const char* name, hid_t rowType) {
  // Validate file handle before using it
  if (file < 0) {
    return -1;
  }

  // Check if dataset already exists - use try/catch approach instead of H5Lexists
  // which has threading issues
  H5E_auto2_t old_func;
  void* old_client_data;
  H5Eget_auto2(H5E_DEFAULT, &old_func, &old_client_data);
  H5Eset_auto2(H5E_DEFAULT, nullptr, nullptr);

  hid_t existing = H5Dopen2(file, name, H5P_DEFAULT);

  H5Eset_auto2(H5E_DEFAULT, old_func, old_client_data);

  if (existing >= 0) {
    return existing;
  }

  // Create new dataset
  hsize_t dims[1] = {0};
  hsize_t maxDims[1] = {H5S_UNLIMITED};
  const hid_t space = H5Screate_simple(1, dims, maxDims);
  const hid_t dcpl = H5Pcreate(H5P_DATASET_CREATE);
  hsize_t chunkDims[1] = {4096};
  H5Pset_chunk(dcpl, 1, chunkDims);

  const hid_t ds = H5Dcreate2(file, name, rowType, space, H5P_DEFAULT, dcpl,
                              H5P_DEFAULT);

  H5Pclose(dcpl);
  H5Sclose(space);
  return ds;
}

bool AppendNativeRows(hid_t dataset,
                      hid_t rowType,
                      const void* data,
                      hsize_t nRows) {
  if (dataset < 0 || rowType < 0 || !data || nRows == 0) {
    return true;
  }

  const hid_t oldSpace = H5Dget_space(dataset);
  hsize_t oldDims[1] = {0};
  H5Sget_simple_extent_dims(oldSpace, oldDims, nullptr);
  H5Sclose(oldSpace);

  hsize_t newDims[1] = {oldDims[0] + nRows};
  if (H5Dset_extent(dataset, newDims) < 0) {
    return false;
  }

  const hid_t fileSpace = H5Dget_space(dataset);
  hsize_t start[1] = {oldDims[0]};
  hsize_t count[1] = {nRows};
  H5Sselect_hyperslab(fileSpace, H5S_SELECT_SET, start, nullptr, count, nullptr);

  const hid_t memSpace = H5Screate_simple(1, count, nullptr);
  const herr_t writeStatus =
      H5Dwrite(dataset, rowType, memSpace, fileSpace, H5P_DEFAULT, data);

  H5Sclose(memSpace);
  H5Sclose(fileSpace);
  return writeStatus >= 0;
}

hid_t CreatePrimaryType() {
  const hid_t speciesType = CreateFixedStringType(kSpeciesLabelSize);
  const hid_t rowType = H5Tcreate(H5T_COMPOUND, sizeof(Hdf5PrimaryNativeRow));

  H5Tinsert(rowType, "gun_call_id",
            HOFFSET(Hdf5PrimaryNativeRow, gun_call_id), H5T_NATIVE_INT64);
  H5Tinsert(rowType, "primary_track_id",
            HOFFSET(Hdf5PrimaryNativeRow, primary_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "primary_species",
            HOFFSET(Hdf5PrimaryNativeRow, primary_species), speciesType);
  H5Tinsert(rowType, "primary_x_mm",
            HOFFSET(Hdf5PrimaryNativeRow, primary_x_mm), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "primary_y_mm",
            HOFFSET(Hdf5PrimaryNativeRow, primary_y_mm), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "primary_energy_MeV",
            HOFFSET(Hdf5PrimaryNativeRow, primary_energy_MeV), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "primary_interaction_time_ns",
            HOFFSET(Hdf5PrimaryNativeRow, primary_interaction_time_ns),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "primary_created_secondary_count",
            HOFFSET(Hdf5PrimaryNativeRow, primary_created_secondary_count),
            H5T_NATIVE_INT64);
  H5Tinsert(rowType, "primary_generated_optical_photon_count",
            HOFFSET(Hdf5PrimaryNativeRow, primary_generated_optical_photon_count),
            H5T_NATIVE_INT64);
  H5Tinsert(rowType, "primary_detected_optical_interface_photon_count",
            HOFFSET(Hdf5PrimaryNativeRow,
                    primary_detected_optical_interface_photon_count),
            H5T_NATIVE_INT64);

  H5Tclose(speciesType);
  return rowType;
}

hid_t CreateSecondaryType() {
  const hid_t speciesType = CreateFixedStringType(kSpeciesLabelSize);
  const hid_t rowType = H5Tcreate(H5T_COMPOUND, sizeof(Hdf5SecondaryNativeRow));

  H5Tinsert(rowType, "gun_call_id",
            HOFFSET(Hdf5SecondaryNativeRow, gun_call_id), H5T_NATIVE_INT64);
  H5Tinsert(rowType, "primary_track_id",
            HOFFSET(Hdf5SecondaryNativeRow, primary_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "secondary_track_id",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "secondary_species",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_species), speciesType);
  H5Tinsert(rowType, "secondary_origin_x_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_origin_x_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_origin_y_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_origin_y_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_origin_z_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_origin_z_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_origin_energy_MeV",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_origin_energy_MeV),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_end_x_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_end_x_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_end_y_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_end_y_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "secondary_end_z_mm",
            HOFFSET(Hdf5SecondaryNativeRow, secondary_end_z_mm),
            H5T_NATIVE_DOUBLE);

  H5Tclose(speciesType);
  return rowType;
}

hid_t CreatePhotonType() {
  const hid_t rowType = H5Tcreate(H5T_COMPOUND, sizeof(Hdf5PhotonNativeRow));

  H5Tinsert(rowType, "gun_call_id",
            HOFFSET(Hdf5PhotonNativeRow, gun_call_id), H5T_NATIVE_INT64);
  H5Tinsert(rowType, "primary_track_id",
            HOFFSET(Hdf5PhotonNativeRow, primary_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "secondary_track_id",
            HOFFSET(Hdf5PhotonNativeRow, secondary_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "photon_track_id",
            HOFFSET(Hdf5PhotonNativeRow, photon_track_id), H5T_NATIVE_INT32);
  H5Tinsert(rowType, "photon_creation_time_ns",
            HOFFSET(Hdf5PhotonNativeRow, photon_creation_time_ns),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_origin_x_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_origin_x_mm), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_origin_y_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_origin_y_mm), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_origin_z_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_origin_z_mm), H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_scint_exit_x_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_scint_exit_x_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_scint_exit_y_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_scint_exit_y_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "photon_scint_exit_z_mm",
            HOFFSET(Hdf5PhotonNativeRow, photon_scint_exit_z_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_x_mm",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_x_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_y_mm",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_y_mm),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_time_ns",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_time_ns),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_dir_x",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_dir_x),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_dir_y",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_dir_y),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_dir_z",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_dir_z),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_pol_x",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_pol_x),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_pol_y",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_pol_y),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_pol_z",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_pol_z),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_energy_eV",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_energy_eV),
            H5T_NATIVE_DOUBLE);
  H5Tinsert(rowType, "optical_interface_hit_wavelength_nm",
            HOFFSET(Hdf5PhotonNativeRow, optical_interface_hit_wavelength_nm),
            H5T_NATIVE_DOUBLE);

  return rowType;
}

enum class DatasetType {
  Primary,
  Secondary,
  Photon
};

bool EnsureReady(const std::string& hdf5Path, DatasetType type, std::string* errorMessage) {
  // This function is called with g_hdf5Mutex already locked from AppendHDF5
  auto& s = GetState(hdf5Path);

  // Quick check if already initialized
  if (s.file >= 0 && s.openPath == hdf5Path && s.dataset >= 0) {
    return true;
  }

  if (s.file >= 0 && s.openPath != hdf5Path) {
    CloseState(s);
  }

  if (!EnsureParentDirectory(hdf5Path)) {
    if (errorMessage) {
      *errorMessage = "Output directory does not exist for " + hdf5Path;
    }
    return false;
  }

  // If file handle doesn't exist, open or create it
  if (s.file < 0) {
    // Try to open existing file first (for threads after master)
    s.file = H5Fopen(hdf5Path.c_str(), H5F_ACC_RDWR, H5P_DEFAULT);
    if (s.file < 0) {
      // File doesn't exist, create it (master thread)
      s.file = H5Fcreate(hdf5Path.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
      if (s.file < 0) {
        if (errorMessage) {
          *errorMessage = "Failed to create " + hdf5Path;
        }
        return false;
      }
    }
    s.openPath = hdf5Path;
  }

  // Only create dataset if not already created
  if (s.dataset < 0) {
    switch (type) {
      case DatasetType::Primary:
        s.datasetType = CreatePrimaryType();
        s.dataset = CreateExtendableDataset(s.file, "/primaries", s.datasetType);
        break;
      case DatasetType::Secondary:
        s.datasetType = CreateSecondaryType();
        s.dataset = CreateExtendableDataset(s.file, "/secondaries", s.datasetType);
        break;
      case DatasetType::Photon:
        s.datasetType = CreatePhotonType();
        s.dataset = CreateExtendableDataset(s.file, "/photons", s.datasetType);
        break;
    }

    if (s.dataset < 0 || s.datasetType < 0) {
      if (errorMessage) {
        *errorMessage = "Failed to initialize dataset in " + hdf5Path;
      }
      return false;
    }
  }

  if (!s.registeredAtExit) {
    std::atexit(CloseAll);
    s.registeredAtExit = true;
  }

  return true;
}

std::vector<Hdf5PrimaryNativeRow> ToNative(const std::vector<PrimaryInfo>& rows) {
  std::vector<Hdf5PrimaryNativeRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    Hdf5PrimaryNativeRow native{};
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

std::vector<Hdf5SecondaryNativeRow> ToNative(const std::vector<SecondaryInfo>& rows) {
  std::vector<Hdf5SecondaryNativeRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    Hdf5SecondaryNativeRow native{};
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

std::vector<Hdf5PhotonNativeRow> ToNative(const std::vector<PhotonInfo>& rows) {
  std::vector<Hdf5PhotonNativeRow> out;
  out.reserve(rows.size());
  for (const auto& row : rows) {
    Hdf5PhotonNativeRow native{};
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

}  // namespace

bool InitHDF5(const HDF5OutputPaths& paths,
              const HDF5OutputSelection& selection,
              std::string* errorMessage) {
  std::lock_guard<std::mutex> lock(g_hdf5Mutex);

  // Disable HDF5 error messages temporarily during initialization
  // HDF5 may report spurious thread-safety errors even with proper mutex protection
  H5E_auto2_t old_func;
  void* old_client_data;
  H5Eget_auto2(H5E_DEFAULT, &old_func, &old_client_data);
  H5Eset_auto2(H5E_DEFAULT, nullptr, nullptr);

  bool success = true;

  // Initialize each selected output file by creating files and datasets eagerly
  // This must happen on the master thread before workers start
  if (selection.primaries) {
    if (!EnsureReady(paths.primaries, DatasetType::Primary, errorMessage)) {
      success = false;
    } else {
      // Force flush to ensure file is fully initialized
      auto& s = GetState(paths.primaries);
      if (s.file >= 0) {
        H5Fflush(s.file, H5F_SCOPE_GLOBAL);
      }
    }
  }
  if (success && selection.secondaries) {
    if (!EnsureReady(paths.secondaries, DatasetType::Secondary, errorMessage)) {
      success = false;
    } else {
      auto& s = GetState(paths.secondaries);
      if (s.file >= 0) {
        H5Fflush(s.file, H5F_SCOPE_GLOBAL);
      }
    }
  }
  if (success && selection.photons) {
    if (!EnsureReady(paths.photons, DatasetType::Photon, errorMessage)) {
      success = false;
    } else {
      auto& s = GetState(paths.photons);
      if (s.file >= 0) {
        H5Fflush(s.file, H5F_SCOPE_GLOBAL);
      }
    }
  }

  // Restore HDF5 error reporting
  H5Eset_auto2(H5E_DEFAULT, old_func, old_client_data);

  return success;
}

bool AppendHDF5(const HDF5OutputPaths& paths,
                const HDF5OutputSelection& selection,
                const std::vector<PrimaryInfo>& primaryRows,
                const std::vector<SecondaryInfo>& secondaryRows,
                const std::vector<PhotonInfo>& photonRows,
                std::string* errorMessage) {
  // Serialize all HDF5 operations to ensure thread safety
  std::lock_guard<std::mutex> lock(g_hdf5Mutex);

  if (selection.primaries && !primaryRows.empty()) {
    if (!EnsureReady(paths.primaries, DatasetType::Primary, errorMessage)) {
      return false;
    }
    auto primaryNative = ToNative(primaryRows);
    auto& s = GetState(paths.primaries);
    if (!AppendNativeRows(s.dataset, s.datasetType, primaryNative.data(),
                          static_cast<hsize_t>(primaryNative.size()))) {
      if (errorMessage) {
        *errorMessage = "Failed appending /primaries rows to " + paths.primaries;
      }
      return false;
    }
  }

  if (selection.secondaries && !secondaryRows.empty()) {
    if (!EnsureReady(paths.secondaries, DatasetType::Secondary, errorMessage)) {
      return false;
    }
    auto secondaryNative = ToNative(secondaryRows);
    auto& s = GetState(paths.secondaries);
    if (!AppendNativeRows(s.dataset, s.datasetType, secondaryNative.data(),
                          static_cast<hsize_t>(secondaryNative.size()))) {
      if (errorMessage) {
        *errorMessage = "Failed appending /secondaries rows to " + paths.secondaries;
      }
      return false;
    }
  }

  if (selection.photons && !photonRows.empty()) {
    if (!EnsureReady(paths.photons, DatasetType::Photon, errorMessage)) {
      return false;
    }
    auto photonNative = ToNative(photonRows);
    auto& s = GetState(paths.photons);
    if (!AppendNativeRows(s.dataset, s.datasetType, photonNative.data(),
                          static_cast<hsize_t>(photonNative.size()))) {
      if (errorMessage) {
        *errorMessage = "Failed appending /photons rows to " + paths.photons;
      }
      return false;
    }
  }

  return true;
}

void CloseHDF5(const std::string& hdf5Path) {
  std::lock_guard<std::mutex> lock(g_hdf5Mutex);
  auto it = tl_stateMap.find(hdf5Path);
  if (it != tl_stateMap.end()) {
    CloseState(it->second);
    tl_stateMap.erase(it);
  }
}

}  // namespace SimIO
