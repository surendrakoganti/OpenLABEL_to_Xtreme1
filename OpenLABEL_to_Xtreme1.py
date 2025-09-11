import json
import uuid
import os

def bbox_to_contour(val):
    cx, cy, w, h = val
    return [
        {"x": cx - w/2, "y": cy - h/2},
        {"x": cx - w/2, "y": cy + h/2},
        {"x": cx + w/2, "y": cy + h/2},
        {"x": cx + w/2, "y": cy - h/2},
    ]

def cuboid_to_contour(val):
    return {
        "size3D": {"x": val[6], "y": val[7], "z": val[8]},
        "center3D": {"x": val[0], "y": val[1], "z": val[2]},
        "rotation3D": {"x": val[3], "y": val[4], "z": val[5]},
    }

def check_consistency(file_name, obj_id, object_data, errors):
    has_bbox = "bbox" in object_data and len(object_data["bbox"]) > 0
    has_cuboid = "cuboid" in object_data and len(object_data["cuboid"]) > 0
    if has_bbox and not has_cuboid:
        errors.append(f"[{file_name}] Error: Object ID {obj_id} has bbox but no cuboid.")

def convert_file(input_path, output_path, ref_objects, errors):
    with open(input_path, "r") as f:
        data = json.load(f)

    file_name = os.path.basename(input_path)
    objects_out = []

    for obj_id, obj in data["openlabel"]["objects"].items():
        obj_type = obj["type"]
        track_id = str(uuid.uuid4())
        track_name = str(obj_id)
        object_data = obj.get("object_data", {})

        check_consistency(file_name, obj_id, object_data, errors)

        # Reference object for IDs
        ref_obj = ref_objects.get(obj_type)
        if not ref_obj:
            continue

        class_id = ref_obj["classId"]
        class_values_ref = {v["name"]: v["id"] for v in ref_obj["classValues"]}

        # --- BBox -> 2D_RECT ---
        for bbox in object_data.get("bbox", []):
            class_values = [
                {"id": class_values_ref[a["name"]], "name": a["name"], "type": "TEXT",
                 "alias": a["name"], "value": str(a["val"]), "isLeaf": True}
                for a in bbox.get("attributes", {}).get("num", [])
            ]
            contour = {
                "points": bbox_to_contour(bbox["val"]),
                "size3D": {"x": 0, "y": 0, "z": 0},
                "center3D": {"x": 0, "y": 0, "z": 0},
                "viewIndex": 0,
                "rotation3D": {"x": 0, "y": 0, "z": 0},
            }
            objects_out.append({
                "id": str(uuid.uuid4()),
                "type": "2D_RECT",
                "classId": class_id,
                "className": obj_type,
                "trackId": track_id,
                "trackName": int(obj_id),
                "classValues": class_values,
                "contour": contour,
                "modelConfidence": None,
                "modelClass": obj_type
            })

        # --- Cuboid -> 3D_BOX ---
        for cuboid in object_data.get("cuboid", []):
            class_values = []
            if "bbox" in object_data and object_data["bbox"]:
                class_values = [
                    {"id": class_values_ref[a["name"]], "name": a["name"], "type": "TEXT",
                     "alias": a["name"], "value": str(a["val"]), "isLeaf": True}
                    for a in object_data["bbox"][0].get("attributes", {}).get("num", [])
                ]
            objects_out.append({
                "id": str(uuid.uuid4()),
                "type": "3D_BOX",
                "classId": class_id,
                "className": obj_type,
                "trackId": track_id,
                "trackName": track_name,
                "classValues": class_values,
                "contour": cuboid_to_contour(cuboid["val"]),
                "modelConfidence": None,
                "modelClass": obj_type
            })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "version": "Xtreme1 v0.6",
            "dataId": data.get("dataId", 0),
            "sourceName": "Ground Truth",
            "classificationValues": None,
            "objects": objects_out
        }, f, indent=4)

def convert_folder(input_folder, output_folder, reference_file):
    with open(reference_file, "r") as f:
        reference_data = json.load(f)
    ref_objects = {obj["className"]: obj for obj in reference_data[0]["objects"]}

    os.makedirs(output_folder, exist_ok=True)
    errors = []
    for file in os.listdir(input_folder):
        if file.endswith(".json"):
            convert_file(os.path.join(input_folder, file),
                         os.path.join(output_folder, file),
                         ref_objects,
                         errors)
    print("Conversion completed.")
    if errors:
        print("\nConsistency check errors:")
        for e in errors:
            print(e)
    else:
        print("\nAll files passed consistency checks.")

# === Specify paths here ===
openlabel_folder = "/tmp/20250905_3d&2d/Heavy_rain/Sequence_0/camera_image_3/openlabel"
output_folder = "/home/hs-coburg.de/sur7933s/Documents/scenes/scene_3"
ref_ontology_classes_file = "/home/hs-coburg.de/sur7933s/Documents/openLabel_to_xtreme1/reference_ontology_wrt_objects.json"

convert_folder(openlabel_folder, output_folder + "/result", ref_ontology_classes_file)
