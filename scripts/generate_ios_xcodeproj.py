"""Generate clients/ios/VisualPose.xcodeproj/project.pbxproj from Swift sources."""

from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "clients" / "ios"
APP = IOS / "VisualPose"
TESTS = IOS / "VisualPoseTests"
CORE_MAP_C = ROOT / "native" / "core_map" / "core_map.c"
CORE_MAP_H = ROOT / "native" / "core_map" / "core_map.h"


def hid(name: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"visualpose:{name}").hex[:24].upper()


def swift_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*.swift") if p.is_file())


def main() -> None:
    app_files = swift_files(APP)
    test_files = swift_files(TESTS) if TESTS.is_dir() else []
    project = IOS / "VisualPose.xcodeproj"
    project.mkdir(parents=True, exist_ok=True)

    pbx_proj = hid("project")
    pbx_app_target = hid("target-app")
    pbx_test_target = hid("target-tests")
    pbx_app_sources = hid("phase-app-sources")
    pbx_test_sources = hid("phase-test-sources")
    pbx_frameworks = hid("phase-frameworks")
    pbx_resources = hid("phase-resources")
    pbx_group_root = hid("group-root")
    pbx_group_app = hid("group-app")
    pbx_group_tests = hid("group-tests")
    pbx_group_native = hid("group-native")
    pbx_plist = hid("file-plist")
    pbx_assets = hid("file-assets")
    pbx_assets_build = hid("build-assets")
    pbx_bridge = hid("file-bridge")
    pbx_c = hid("file-core-c")
    pbx_h = hid("file-core-h")
    pbx_cfg_app_d = hid("cfg-app-debug")
    pbx_cfg_app_r = hid("cfg-app-release")
    pbx_cfg_test_d = hid("cfg-test-debug")
    pbx_cfg_proj_d = hid("cfg-proj-debug")
    pbx_cfg_proj_r = hid("cfg-proj-release")
    pbx_list_proj = hid("list-proj")
    pbx_list_app = hid("list-app")
    pbx_list_test = hid("list-test")

    file_ids = {p: hid(f"swift:{p.relative_to(IOS)}") for p in app_files + test_files}
    build_ids = {p: hid(f"build:{p.relative_to(IOS)}") for p in app_files + test_files}
    build_c = hid("build-core-c")

    def fileref(pid: str, path: Path, rel: str) -> str:
        return (
            f"\t\t{pid} /* {path.name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; "
            f"path = {path.name}; sourceTree = \"<group>\"; }};"
        )

    lines: list[str] = []
    lines.append("// !$*UTF8*$!")
    lines.append("{")
    lines.append("\tarchiveVersion = 1;")
    lines.append("\tclasses = {")
    lines.append("\t};")
    lines.append("\tobjectVersion = 56;")
    lines.append("\tobjects = {")
    lines.append("\n/* Begin PBXBuildFile section */")
    for p in app_files:
        lines.append(
            f"\t\t{build_ids[p]} /* {p.name} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_ids[p]} /* {p.name} */; }};"
        )
    for p in test_files:
        lines.append(
            f"\t\t{build_ids[p]} /* {p.name} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_ids[p]} /* {p.name} */; }};"
        )
    lines.append(
        f"\t\t{build_c} /* core_map.c in Sources */ = {{isa = PBXBuildFile; fileRef = {pbx_c} /* core_map.c */; }};"
    )
    lines.append("/* End PBXBuildFile section */\n")

    lines.append("/* Begin PBXFileReference section */")
    lines.append(
        f"\t\t{hid('product-app')} /* VisualPose.app */ = "
        "{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = VisualPose.app; sourceTree = BUILT_PRODUCTS_DIR; };"
    )
    lines.append(
        f"\t\t{hid('product-tests')} /* VisualPoseTests.xctest */ = "
        "{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = VisualPoseTests.xctest; sourceTree = BUILT_PRODUCTS_DIR; };"
    )
    for p in app_files + test_files:
        lines.append(
            f"\t\t{file_ids[p]} /* {p.name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {p.name}; sourceTree = \"<group>\"; }};"
        )
    lines.append(
        f"\t\t{pbx_plist} /* Info.plist */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = \"<group>\"; }};"
    )
    lines.append(
        f"\t\t{pbx_assets} /* Assets.xcassets */ = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = \"<group>\"; }};"
    )
    lines.append(
        f"\t\t{pbx_assets_build} /* Assets.xcassets in Resources */ = {{isa = PBXBuildFile; fileRef = {pbx_assets} /* Assets.xcassets */; }};"
    )
    lines.append(
        f"\t\t{pbx_bridge} /* VisualPose-Bridging-Header.h */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = \"VisualPose-Bridging-Header.h\"; sourceTree = \"<group>\"; }};"
    )
    lines.append(
        f"\t\t{pbx_c} /* core_map.c */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.c; name = core_map.c; path = ../../native/core_map/core_map.c; sourceTree = SOURCE_ROOT; }};"
    )
    lines.append(
        f"\t\t{pbx_h} /* core_map.h */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; name = core_map.h; path = ../../native/core_map/core_map.h; sourceTree = SOURCE_ROOT; }};"
    )
    lines.append("/* End PBXFileReference section */\n")

    app_children = " ".join(f"{file_ids[p]} /* {p.name} */," for p in app_files)
    test_children = " ".join(f"{file_ids[p]} /* {p.name} */," for p in test_files)
    lines.append("/* Begin PBXGroup section */")
    lines.append(f"\t\t{pbx_group_root} = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{pbx_group_app} /* VisualPose */,")
    lines.append(f"\t\t\t\t{pbx_group_tests} /* VisualPoseTests */,")
    lines.append(f"\t\t\t\t{pbx_group_native} /* core_map */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append(f"\t\t{pbx_group_app} /* VisualPose */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    for p in app_files:
        lines.append(f"\t\t\t\t{file_ids[p]} /* {p.name} */,")
    lines.append(f"\t\t\t\t{pbx_plist} /* Info.plist */,")
    lines.append(f"\t\t\t\t{pbx_assets} /* Assets.xcassets */,")
    lines.append(f"\t\t\t\t{pbx_bridge} /* VisualPose-Bridging-Header.h */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tpath = VisualPose;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append(f"\t\t{pbx_group_tests} /* VisualPoseTests */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    for p in test_files:
        lines.append(f"\t\t\t\t{file_ids[p]} /* {p.name} */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tpath = VisualPoseTests;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append(f"\t\t{pbx_group_native} /* core_map */ = {{")
    lines.append("\t\t\tisa = PBXGroup;")
    lines.append("\t\t\tchildren = (")
    lines.append(f"\t\t\t\t{pbx_c} /* core_map.c */,")
    lines.append(f"\t\t\t\t{pbx_h} /* core_map.h */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = core_map;")
    lines.append("\t\t\tsourceTree = \"<group>\";")
    lines.append("\t\t};")
    lines.append("/* End PBXGroup section */\n")

    lines.append("/* Begin PBXNativeTarget section */")
    lines.append(f"\t\t{pbx_app_target} /* VisualPose */ = {{")
    lines.append("\t\t\tisa = PBXNativeTarget;")
    lines.append("\t\t\tbuildConfigurationList = " + pbx_list_app + " /* Build configuration list for PBXNativeTarget \"VisualPose\" */;")
    lines.append("\t\t\tbuildPhases = (")
    lines.append(f"\t\t\t\t{hid('phase-copy')} /* Copy shared assets */,")
    lines.append(f"\t\t\t\t{pbx_app_sources} /* Sources */,")
    lines.append(f"\t\t\t\t{pbx_frameworks} /* Frameworks */,")
    lines.append(f"\t\t\t\t{pbx_resources} /* Resources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tbuildRules = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdependencies = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = VisualPose;")
    lines.append("\t\t\tproductName = VisualPose;")
    lines.append(f"\t\t\tproductReference = {hid('product-app')} /* VisualPose.app */;")
    lines.append("\t\t\tproductType = \"com.apple.product-type.application\";")
    lines.append("\t\t};")
    lines.append(f"\t\t{pbx_test_target} /* VisualPoseTests */ = {{")
    lines.append("\t\t\tisa = PBXNativeTarget;")
    lines.append("\t\t\tbuildConfigurationList = " + pbx_list_test + " /* Build configuration list for PBXNativeTarget \"VisualPoseTests\" */;")
    lines.append("\t\t\tbuildPhases = (")
    lines.append(f"\t\t\t\t{pbx_test_sources} /* Sources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\tbuildRules = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tdependencies = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = VisualPoseTests;")
    lines.append("\t\t\tproductName = VisualPoseTests;")
    lines.append(f"\t\t\tproductReference = {hid('product-tests')} /* VisualPoseTests.xctest */;")
    lines.append("\t\t\tproductType = \"com.apple.product-type.bundle.unit-test\";")
    lines.append("\t\t};")
    lines.append("/* End PBXNativeTarget section */\n")

    lines.append("/* Begin PBXProject section */")
    lines.append(f"\t\t{pbx_proj} /* Project object */ = {{")
    lines.append("\t\t\tisa = PBXProject;")
    lines.append("\t\t\tattributes = {")
    lines.append("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    lines.append("\t\t\t\tLastSwiftUpdateCheck = 1600;")
    lines.append("\t\t\t\tLastUpgradeCheck = 1600;")
    lines.append("\t\t\t};")
    lines.append(f"\t\t\tbuildConfigurationList = {pbx_list_proj} /* Build configuration list for PBXProject \"VisualPose\" */;")
    lines.append("\t\t\tcompatibilityVersion = \"Xcode 14.0\";")
    lines.append("\t\t\tdevelopmentRegion = en;")
    lines.append("\t\t\thasScannedForEncodings = 0;")
    lines.append("\t\t\tknownRegions = (")
    lines.append("\t\t\t\ten,")
    lines.append("\t\t\t\tBase,")
    lines.append("\t\t\t);")
    lines.append(f"\t\t\tmainGroup = {pbx_group_root};")
    lines.append("\t\t\tproductRefGroup = " + pbx_group_root + ";")
    lines.append("\t\t\tprojectDirPath = \"\";")
    lines.append("\t\t\tprojectRoot = \"\";")
    lines.append("\t\t\ttargets = (")
    lines.append(f"\t\t\t\t{pbx_app_target} /* VisualPose */,")
    lines.append(f"\t\t\t\t{pbx_test_target} /* VisualPoseTests */,")
    lines.append("\t\t\t);")
    lines.append("\t\t};")
    lines.append("/* End PBXProject section */\n")

    copy_id = hid("phase-copy")
    lines.append("/* Begin PBXShellScriptBuildPhase section */")
    lines.append(f"\t\t{copy_id} /* Copy shared assets */ = {{")
    lines.append("\t\t\tisa = PBXShellScriptBuildPhase;")
    lines.append("\t\t\talwaysOutOfDate = 1;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tinputPaths = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\tname = \"Copy shared assets\";")
    lines.append("\t\t\toutputPaths = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    copy_script = (
        'ROOT="$SRCROOT/../.."; DEST="$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"; '
        'cp -f "$ROOT/locales/strings.json" "$DEST/strings.json"; '
        'cp -f "$ROOT/content/ski/curriculum.v2.json" "$DEST/curriculum.v2.json"; '
        'cp -f "$ROOT/models/pose_landmarker_full.task" "$DEST/pose_landmarker_full.task";'
    )
    escaped = copy_script.replace("\\", "\\\\").replace('"', '\\"')
    lines.append(f'\t\t\tshellScript = "{escaped}\\n";')
    lines.append("\t\t\tshellPath = /bin/sh;")
    lines.append("\t\t};")
    lines.append("/* End PBXShellScriptBuildPhase section */\n")

    lines.append("/* Begin PBXSourcesBuildPhase section */")
    lines.append(f"\t\t{pbx_app_sources} /* Sources */ = {{")
    lines.append("\t\t\tisa = PBXSourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    for p in app_files:
        lines.append(f"\t\t\t\t{build_ids[p]} /* {p.name} in Sources */,")
    lines.append(f"\t\t\t\t{build_c} /* core_map.c in Sources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append(f"\t\t{pbx_test_sources} /* Sources */ = {{")
    lines.append("\t\t\tisa = PBXSourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    for p in test_files:
        lines.append(f"\t\t\t\t{build_ids[p]} /* {p.name} in Sources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXSourcesBuildPhase section */\n")

    lines.append("/* Begin PBXFrameworksBuildPhase section */")
    lines.append(f"\t\t{pbx_frameworks} /* Frameworks */ = {{")
    lines.append("\t\t\tisa = PBXFrameworksBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXFrameworksBuildPhase section */\n")

    lines.append("/* Begin PBXResourcesBuildPhase section */")
    lines.append(f"\t\t{pbx_resources} /* Resources */ = {{")
    lines.append("\t\t\tisa = PBXResourcesBuildPhase;")
    lines.append("\t\t\tbuildActionMask = 2147483647;")
    lines.append("\t\t\tfiles = (")
    lines.append(f"\t\t\t\t{pbx_assets_build} /* Assets.xcassets in Resources */,")
    lines.append("\t\t\t);")
    lines.append("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    lines.append("\t\t};")
    lines.append("/* End PBXResourcesBuildPhase section */\n")

    def xcconfig(pid: str, name: str, extra: str) -> None:
        lines.append(f"\t\t{pid} /* {name} */ = {{")
        lines.append("\t\t\tisa = XCBuildConfiguration;")
        lines.append("\t\t\tbuildSettings = {")
        lines.append(extra)
        lines.append("\t\t\t};")
        lines.append(f"\t\t\tname = {name};")
        lines.append("\t\t};")

    proj_settings = """
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				SDKROOT = iphoneos;
				SWIFT_VERSION = 5.0;
"""
    app_debug = """
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_IDENTITY = "";
				CODE_SIGN_STYLE = Manual;
				CODE_SIGNING_ALLOWED = NO;
				CODE_SIGNING_REQUIRED = NO;
				CURRENT_PROJECT_VERSION = 1;
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = VisualPose/Info.plist;
				LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks";
				MARKETING_VERSION = 0.1.0;
				PRODUCT_BUNDLE_IDENTIFIER = local.visual.corepose;
				PRODUCT_NAME = "$(TARGET_NAME)";
				PROVISIONING_PROFILE_SPECIFIER = "";
				SWIFT_EMIT_LOC_STRINGS = NO;
				SWIFT_OBJC_BRIDGING_HEADER = "VisualPose/VisualPose-Bridging-Header.h";
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = 1;
				HEADER_SEARCH_PATHS = "$(SRCROOT)/../../native/core_map";
"""
    app_rel = app_debug.replace('SWIFT_OPTIMIZATION_LEVEL = "-Onone";\n', "")
    test_settings = """
				BUNDLE_LOADER = "$(TEST_HOST)";
				CODE_SIGN_STYLE = Automatic;
				GENERATE_INFOPLIST_FILE = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				PRODUCT_BUNDLE_IDENTIFIER = local.visual.corepose.tests;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = 1;
				TEST_HOST = "$(BUILT_PRODUCTS_DIR)/VisualPose.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/VisualPose";
				HEADER_SEARCH_PATHS = "$(SRCROOT)/../../native/core_map";
"""

    lines.append("/* Begin XCBuildConfiguration section */")
    xcconfig(pbx_cfg_proj_d, "Debug", proj_settings)
    xcconfig(pbx_cfg_proj_r, "Release", proj_settings)
    xcconfig(pbx_cfg_app_d, "Debug", app_debug)
    xcconfig(pbx_cfg_app_r, "Release", app_rel)
    xcconfig(pbx_cfg_test_d, "Debug", test_settings)
    lines.append("/* End XCBuildConfiguration section */\n")

    def xclist(pid: str, title: str, cfgs: list[tuple[str, str]]) -> None:
        lines.append(f"\t\t{pid} /* {title} */ = {{")
        lines.append("\t\t\tisa = XCConfigurationList;")
        lines.append("\t\t\tbuildConfigurations = (")
        for cid, name in cfgs:
            lines.append(f"\t\t\t\t{cid} /* {name} */,")
        lines.append("\t\t\t);")
        lines.append("\t\t\tdefaultConfigurationIsVisible = 0;")
        lines.append("\t\t\tdefaultConfigurationName = Release;")
        lines.append("\t\t};")

    lines.append("/* Begin XCConfigurationList section */")
    xclist(pbx_list_proj, 'Build configuration list for PBXProject "VisualPose"', [(pbx_cfg_proj_d, "Debug"), (pbx_cfg_proj_r, "Release")])
    xclist(pbx_list_app, 'Build configuration list for PBXNativeTarget "VisualPose"', [(pbx_cfg_app_d, "Debug"), (pbx_cfg_app_r, "Release")])
    xclist(pbx_list_test, 'Build configuration list for PBXNativeTarget "VisualPoseTests"', [(pbx_cfg_test_d, "Debug")])
    lines.append("/* End XCConfigurationList section */")
    lines.append("\t};")
    lines.append(f"\trootObject = {pbx_proj} /* Project object */;")
    lines.append("}")

    (project / "project.pbxproj").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {project / 'project.pbxproj'} ({len(app_files)} app, {len(test_files)} tests)")

    # Write workspace contents file (required for SPM resolution)
    ws_dir = project / "project.xcworkspace"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "contents.xcworkspacedata").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Workspace version = "1.0">\n'
        '   <FileRef location = "self:"></FileRef>\n'
        '</Workspace>\n',
        encoding="utf-8",
    )

    # Write shared scheme so xcodebuild can find it without opening Xcode first
    schemes_dir = project / "xcshareddata" / "xcschemes"
    schemes_dir.mkdir(parents=True, exist_ok=True)
    scheme_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.7">
   <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES">
      <BuildActionEntries>
         <BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">
            <BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{pbx_app_target}" BuildableName="VisualPose.app" BlueprintName="VisualPose" ReferencedContainer="container:VisualPose.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.DebuggerFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES">
      <Testables>
         <TestableReference skipped="NO">
            <BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{pbx_test_target}" BuildableName="VisualPoseTests.xctest" BlueprintName="VisualPoseTests" ReferencedContainer="container:VisualPose.xcodeproj">
            </BuildableReference>
         </TestableReference>
      </Testables>
   </TestAction>
   <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.DebuggerFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES">
      <BuildableProductRunnable runnableDebuggingMode="0">
         <BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{pbx_app_target}" BuildableName="VisualPose.app" BlueprintName="VisualPose" ReferencedContainer="container:VisualPose.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
</Scheme>
"""
    (schemes_dir / "VisualPose.xcscheme").write_text(scheme_xml, encoding="utf-8")
    print(f"Wrote {schemes_dir / 'VisualPose.xcscheme'}")


if __name__ == "__main__":
    main()
