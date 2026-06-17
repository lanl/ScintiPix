#include "SimIO.hh"
#include "utils.hh"

#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>

#include <cctype>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace SimIO {
namespace {
/// Stage subdirectory for raw simulation output.
constexpr const char* kSimulatedPhotonsDir = "simulatedPhotons";

std::filesystem::path AppendSimulatedPhotonsDir(std::filesystem::path path) {
  if (path.filename() == kSimulatedPhotonsDir) {
    return path;
  }
  return path / kSimulatedPhotonsDir;
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

std::string ErrorText(const arrow::Status& status) {
  return status.ToString();
}

template <typename Builder, typename Value>
bool AppendValue(Builder& builder, Value value, std::string* errorMessage) {
  const auto status = builder.Append(value);
  if (!status.ok()) {
    if (errorMessage) {
      *errorMessage = ErrorText(status);
    }
    return false;
  }
  return true;
}

bool AppendString(arrow::StringBuilder& builder,
                  const std::string& value,
                  std::string* errorMessage) {
  const auto status = builder.Append(value);
  if (!status.ok()) {
    if (errorMessage) {
      *errorMessage = ErrorText(status);
    }
    return false;
  }
  return true;
}

template <typename Builder>
std::shared_ptr<arrow::Array> FinishArray(Builder& builder,
                                          std::string* errorMessage) {
  std::shared_ptr<arrow::Array> array;
  const auto status = builder.Finish(&array);
  if (!status.ok()) {
    if (errorMessage) {
      *errorMessage = ErrorText(status);
    }
    return nullptr;
  }
  return array;
}

bool WriteTable(const std::string& path,
                const std::shared_ptr<arrow::Table>& table,
                std::string* errorMessage) {
  if (!EnsureParentDirectory(path)) {
    if (errorMessage) {
      *errorMessage = "Output directory does not exist for " + path;
    }
    return false;
  }

  auto maybeOutput = arrow::io::FileOutputStream::Open(path);
  if (!maybeOutput.ok()) {
    if (errorMessage) {
      *errorMessage = ErrorText(maybeOutput.status());
    }
    return false;
  }

  const auto status =
      parquet::arrow::WriteTable(*table, arrow::default_memory_pool(),
                                 *maybeOutput, 4096);
  if (!status.ok()) {
    if (errorMessage) {
      *errorMessage = ErrorText(status);
    }
    return false;
  }
  return true;
}

bool WritePrimaries(const std::string& path,
                    const std::vector<PrimaryInfo>& rows,
                    std::string* errorMessage) {
  arrow::Int64Builder gunCallId;
  arrow::Int32Builder primaryTrackId;
  arrow::StringBuilder primarySpecies;
  arrow::DoubleBuilder primaryXmm;
  arrow::DoubleBuilder primaryYmm;
  arrow::DoubleBuilder primaryEnergyMeV;
  arrow::DoubleBuilder primaryInteractionTimeNs;
  arrow::Int64Builder primaryCreatedSecondaryCount;
  arrow::Int64Builder primaryGeneratedOpticalPhotonCount;
  arrow::Int64Builder primaryDetectedOpticalInterfacePhotonCount;

  for (const auto& row : rows) {
    if (!AppendValue(gunCallId, row.gunCallId, errorMessage) ||
        !AppendValue(primaryTrackId, row.primaryTrackId, errorMessage) ||
        !AppendString(primarySpecies, row.primarySpecies, errorMessage) ||
        !AppendValue(primaryXmm, row.primaryXmm, errorMessage) ||
        !AppendValue(primaryYmm, row.primaryYmm, errorMessage) ||
        !AppendValue(primaryEnergyMeV, row.primaryEnergyMeV, errorMessage) ||
        !AppendValue(primaryInteractionTimeNs, row.primaryInteractionTimeNs,
                     errorMessage) ||
        !AppendValue(primaryCreatedSecondaryCount,
                     row.primaryCreatedSecondaryCount, errorMessage) ||
        !AppendValue(primaryGeneratedOpticalPhotonCount,
                     row.primaryGeneratedOpticalPhotonCount, errorMessage) ||
        !AppendValue(primaryDetectedOpticalInterfacePhotonCount,
                     row.primaryDetectedOpticalInterfacePhotonCount,
                     errorMessage)) {
      return false;
    }
  }

  auto schema = arrow::schema({
      arrow::field("gun_call_id", arrow::int64()),
      arrow::field("primary_track_id", arrow::int32()),
      arrow::field("primary_species", arrow::utf8()),
      arrow::field("primary_x_mm", arrow::float64()),
      arrow::field("primary_y_mm", arrow::float64()),
      arrow::field("primary_energy_MeV", arrow::float64()),
      arrow::field("primary_interaction_time_ns", arrow::float64()),
      arrow::field("primary_created_secondary_count", arrow::int64()),
      arrow::field("primary_generated_optical_photon_count", arrow::int64()),
      arrow::field("primary_detected_optical_interface_photon_count",
                   arrow::int64()),
  });

  auto table = arrow::Table::Make(
      schema,
      {
          FinishArray(gunCallId, errorMessage),
          FinishArray(primaryTrackId, errorMessage),
          FinishArray(primarySpecies, errorMessage),
          FinishArray(primaryXmm, errorMessage),
          FinishArray(primaryYmm, errorMessage),
          FinishArray(primaryEnergyMeV, errorMessage),
          FinishArray(primaryInteractionTimeNs, errorMessage),
          FinishArray(primaryCreatedSecondaryCount, errorMessage),
          FinishArray(primaryGeneratedOpticalPhotonCount, errorMessage),
          FinishArray(primaryDetectedOpticalInterfacePhotonCount, errorMessage),
      });
  return !table->columns().empty() && WriteTable(path, table, errorMessage);
}

bool WriteSecondaries(const std::string& path,
                      const std::vector<SecondaryInfo>& rows,
                      std::string* errorMessage) {
  arrow::Int64Builder gunCallId;
  arrow::Int32Builder primaryTrackId;
  arrow::Int32Builder secondaryTrackId;
  arrow::StringBuilder secondarySpecies;
  arrow::DoubleBuilder secondaryOriginXmm;
  arrow::DoubleBuilder secondaryOriginYmm;
  arrow::DoubleBuilder secondaryOriginZmm;
  arrow::DoubleBuilder secondaryOriginEnergyMeV;
  arrow::DoubleBuilder secondaryEndXmm;
  arrow::DoubleBuilder secondaryEndYmm;
  arrow::DoubleBuilder secondaryEndZmm;

  for (const auto& row : rows) {
    if (!AppendValue(gunCallId, row.gunCallId, errorMessage) ||
        !AppendValue(primaryTrackId, row.primaryTrackId, errorMessage) ||
        !AppendValue(secondaryTrackId, row.secondaryTrackId, errorMessage) ||
        !AppendString(secondarySpecies, row.secondarySpecies, errorMessage) ||
        !AppendValue(secondaryOriginXmm, row.secondaryOriginXmm, errorMessage) ||
        !AppendValue(secondaryOriginYmm, row.secondaryOriginYmm, errorMessage) ||
        !AppendValue(secondaryOriginZmm, row.secondaryOriginZmm, errorMessage) ||
        !AppendValue(secondaryOriginEnergyMeV, row.secondaryOriginEnergyMeV,
                     errorMessage) ||
        !AppendValue(secondaryEndXmm, row.secondaryEndXmm, errorMessage) ||
        !AppendValue(secondaryEndYmm, row.secondaryEndYmm, errorMessage) ||
        !AppendValue(secondaryEndZmm, row.secondaryEndZmm, errorMessage)) {
      return false;
    }
  }

  auto schema = arrow::schema({
      arrow::field("gun_call_id", arrow::int64()),
      arrow::field("primary_track_id", arrow::int32()),
      arrow::field("secondary_track_id", arrow::int32()),
      arrow::field("secondary_species", arrow::utf8()),
      arrow::field("secondary_origin_x_mm", arrow::float64()),
      arrow::field("secondary_origin_y_mm", arrow::float64()),
      arrow::field("secondary_origin_z_mm", arrow::float64()),
      arrow::field("secondary_origin_energy_MeV", arrow::float64()),
      arrow::field("secondary_end_x_mm", arrow::float64()),
      arrow::field("secondary_end_y_mm", arrow::float64()),
      arrow::field("secondary_end_z_mm", arrow::float64()),
  });

  auto table = arrow::Table::Make(
      schema,
      {
          FinishArray(gunCallId, errorMessage),
          FinishArray(primaryTrackId, errorMessage),
          FinishArray(secondaryTrackId, errorMessage),
          FinishArray(secondarySpecies, errorMessage),
          FinishArray(secondaryOriginXmm, errorMessage),
          FinishArray(secondaryOriginYmm, errorMessage),
          FinishArray(secondaryOriginZmm, errorMessage),
          FinishArray(secondaryOriginEnergyMeV, errorMessage),
          FinishArray(secondaryEndXmm, errorMessage),
          FinishArray(secondaryEndYmm, errorMessage),
          FinishArray(secondaryEndZmm, errorMessage),
      });
  return !table->columns().empty() && WriteTable(path, table, errorMessage);
}

bool WritePhotons(const std::string& path,
                  const std::vector<PhotonInfo>& rows,
                  std::string* errorMessage) {
  arrow::Int64Builder gunCallId;
  arrow::Int32Builder primaryTrackId;
  arrow::Int32Builder secondaryTrackId;
  arrow::Int32Builder photonTrackId;
  arrow::DoubleBuilder photonCreationTimeNs;
  arrow::DoubleBuilder photonOriginXmm;
  arrow::DoubleBuilder photonOriginYmm;
  arrow::DoubleBuilder photonOriginZmm;
  arrow::DoubleBuilder photonScintExitXmm;
  arrow::DoubleBuilder photonScintExitYmm;
  arrow::DoubleBuilder photonScintExitZmm;
  arrow::DoubleBuilder opticalInterfaceHitXmm;
  arrow::DoubleBuilder opticalInterfaceHitYmm;
  arrow::DoubleBuilder opticalInterfaceHitTimeNs;
  arrow::DoubleBuilder opticalInterfaceHitDirX;
  arrow::DoubleBuilder opticalInterfaceHitDirY;
  arrow::DoubleBuilder opticalInterfaceHitDirZ;
  arrow::DoubleBuilder opticalInterfaceHitPolX;
  arrow::DoubleBuilder opticalInterfaceHitPolY;
  arrow::DoubleBuilder opticalInterfaceHitPolZ;
  arrow::DoubleBuilder opticalInterfaceHitEnergyEV;
  arrow::DoubleBuilder opticalInterfaceHitWavelengthNm;

  for (const auto& row : rows) {
    if (!AppendValue(gunCallId, row.gunCallId, errorMessage) ||
        !AppendValue(primaryTrackId, row.primaryTrackId, errorMessage) ||
        !AppendValue(secondaryTrackId, row.secondaryTrackId, errorMessage) ||
        !AppendValue(photonTrackId, row.photonTrackId, errorMessage) ||
        !AppendValue(photonCreationTimeNs, row.photonCreationTimeNs,
                     errorMessage) ||
        !AppendValue(photonOriginXmm, row.photonOriginXmm, errorMessage) ||
        !AppendValue(photonOriginYmm, row.photonOriginYmm, errorMessage) ||
        !AppendValue(photonOriginZmm, row.photonOriginZmm, errorMessage) ||
        !AppendValue(photonScintExitXmm, row.photonScintExitXmm,
                     errorMessage) ||
        !AppendValue(photonScintExitYmm, row.photonScintExitYmm,
                     errorMessage) ||
        !AppendValue(photonScintExitZmm, row.photonScintExitZmm,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitXmm, row.opticalInterfaceHitXmm,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitYmm, row.opticalInterfaceHitYmm,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitTimeNs, row.opticalInterfaceHitTimeNs,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitDirX, row.opticalInterfaceHitDirX,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitDirY, row.opticalInterfaceHitDirY,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitDirZ, row.opticalInterfaceHitDirZ,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitPolX, row.opticalInterfaceHitPolX,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitPolY, row.opticalInterfaceHitPolY,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitPolZ, row.opticalInterfaceHitPolZ,
                     errorMessage) ||
        !AppendValue(opticalInterfaceHitEnergyEV,
                     row.opticalInterfaceHitEnergyEV, errorMessage) ||
        !AppendValue(opticalInterfaceHitWavelengthNm,
                     row.opticalInterfaceHitWavelengthNm, errorMessage)) {
      return false;
    }
  }

  auto schema = arrow::schema({
      arrow::field("gun_call_id", arrow::int64()),
      arrow::field("primary_track_id", arrow::int32()),
      arrow::field("secondary_track_id", arrow::int32()),
      arrow::field("photon_track_id", arrow::int32()),
      arrow::field("photon_creation_time_ns", arrow::float64()),
      arrow::field("photon_origin_x_mm", arrow::float64()),
      arrow::field("photon_origin_y_mm", arrow::float64()),
      arrow::field("photon_origin_z_mm", arrow::float64()),
      arrow::field("photon_scint_exit_x_mm", arrow::float64()),
      arrow::field("photon_scint_exit_y_mm", arrow::float64()),
      arrow::field("photon_scint_exit_z_mm", arrow::float64()),
      arrow::field("optical_interface_hit_x_mm", arrow::float64()),
      arrow::field("optical_interface_hit_y_mm", arrow::float64()),
      arrow::field("optical_interface_hit_time_ns", arrow::float64()),
      arrow::field("optical_interface_hit_dir_x", arrow::float64()),
      arrow::field("optical_interface_hit_dir_y", arrow::float64()),
      arrow::field("optical_interface_hit_dir_z", arrow::float64()),
      arrow::field("optical_interface_hit_pol_x", arrow::float64()),
      arrow::field("optical_interface_hit_pol_y", arrow::float64()),
      arrow::field("optical_interface_hit_pol_z", arrow::float64()),
      arrow::field("optical_interface_hit_energy_eV", arrow::float64()),
      arrow::field("optical_interface_hit_wavelength_nm", arrow::float64()),
  });

  auto table = arrow::Table::Make(
      schema,
      {
          FinishArray(gunCallId, errorMessage),
          FinishArray(primaryTrackId, errorMessage),
          FinishArray(secondaryTrackId, errorMessage),
          FinishArray(photonTrackId, errorMessage),
          FinishArray(photonCreationTimeNs, errorMessage),
          FinishArray(photonOriginXmm, errorMessage),
          FinishArray(photonOriginYmm, errorMessage),
          FinishArray(photonOriginZmm, errorMessage),
          FinishArray(photonScintExitXmm, errorMessage),
          FinishArray(photonScintExitYmm, errorMessage),
          FinishArray(photonScintExitZmm, errorMessage),
          FinishArray(opticalInterfaceHitXmm, errorMessage),
          FinishArray(opticalInterfaceHitYmm, errorMessage),
          FinishArray(opticalInterfaceHitTimeNs, errorMessage),
          FinishArray(opticalInterfaceHitDirX, errorMessage),
          FinishArray(opticalInterfaceHitDirY, errorMessage),
          FinishArray(opticalInterfaceHitDirZ, errorMessage),
          FinishArray(opticalInterfaceHitPolX, errorMessage),
          FinishArray(opticalInterfaceHitPolY, errorMessage),
          FinishArray(opticalInterfaceHitPolZ, errorMessage),
          FinishArray(opticalInterfaceHitEnergyEV, errorMessage),
          FinishArray(opticalInterfaceHitWavelengthNm, errorMessage),
      });
  return !table->columns().empty() && WriteTable(path, table, errorMessage);
}
}  // namespace

// Normalize a run name into a directory-safe token.
std::string NormalizeRunName(const std::string& value) {
  std::string normalized = Utils::Unquote(Utils::Trim(value));

  for (char& c : normalized) {
    const unsigned char uc = static_cast<unsigned char>(c);
    if (c == '/' || c == '\\' || std::isspace(uc)) {
      c = '_';
    }
  }

  return normalized;
}

// Strip known output suffixes when present.
std::string StripKnownOutputExtension(const std::string& value) {
  const std::filesystem::path path(value);
  const std::string ext = Utils::ToLower(path.extension().string());

  if (ext != ".h5" && ext != ".hdf5" && ext != ".parquet") {
    return value;
  }

  const std::filesystem::path base = path.parent_path() / path.stem();
  return base.string();
}

// Resolve a relative path against repository root (or cwd fallback).
std::filesystem::path ResolveAgainstRepositoryRoot(std::filesystem::path path) {
  if (!path.is_relative()) {
    return path;
  }
#ifdef SCINTIPIX_REPO_ROOT
  return std::filesystem::path(SCINTIPIX_REPO_ROOT) / path;
#else
  return std::filesystem::current_path() / path;
#endif
}


// Compose absolute output path from base name, output path override, and run name.
std::string ComposeOutputPath(const std::string& base,
                              const std::string& outputPath,
                              const std::string& runName,
                              const char* extension) {
  const std::string safeBase =
      base.empty() ? "data/photon_optical_interface_hits" : base;

  std::filesystem::path basePath = ResolveAgainstRepositoryRoot(safeBase);
  const std::string baseLeaf = basePath.filename().string().empty()
                                   ? "photon_optical_interface_hits"
                                   : basePath.filename().string();

  if (!outputPath.empty()) {
    std::filesystem::path explicitDir = ResolveAgainstRepositoryRoot(outputPath);
    if (!runName.empty()) {
      explicitDir /= runName;
    }
    explicitDir = AppendSimulatedPhotonsDir(explicitDir);
    return (explicitDir / baseLeaf).string() + extension;
  }

  if (runName.empty()) {
    std::filesystem::path root = basePath.parent_path();
    if (root.empty()) {
#ifdef SCINTIPIX_REPO_ROOT
      root = std::filesystem::path(SCINTIPIX_REPO_ROOT) / "data";
#else
      root = std::filesystem::current_path() / "data";
#endif
    }
    root = AppendSimulatedPhotonsDir(root);
    return (root / baseLeaf).string() + extension;
  }

#ifdef SCINTIPIX_REPO_ROOT
  std::filesystem::path runDir =
      std::filesystem::path(SCINTIPIX_REPO_ROOT) / "data" / runName;
#else
  std::filesystem::path runDir =
      std::filesystem::current_path() / "data" / runName;
#endif
  runDir = AppendSimulatedPhotonsDir(runDir);

  return (runDir / baseLeaf).string() + extension;
}

ParquetOutputPaths ParquetPathsForBase(const std::string& basePath) {
  const std::filesystem::path path = StripKnownOutputExtension(basePath);
  const std::filesystem::path parent = path.parent_path();
  const std::string stem = path.filename().string();

  return {
      (parent / (stem + "_primaries.parquet")).string(),
      (parent / (stem + "_secondaries.parquet")).string(),
      (parent / (stem + "_photons.parquet")).string(),
  };
}

bool WriteParquet(const std::string& basePath,
                  const std::vector<PrimaryInfo>& primaryRows,
                  const std::vector<SecondaryInfo>& secondaryRows,
                  const std::vector<PhotonInfo>& photonRows,
                  std::string* errorMessage) {
  const auto paths = ParquetPathsForBase(basePath);
  return WritePrimaries(paths.primaries, primaryRows, errorMessage) &&
         WriteSecondaries(paths.secondaries, secondaryRows, errorMessage) &&
         WritePhotons(paths.photons, photonRows, errorMessage);
}

}  // namespace SimIO
