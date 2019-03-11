from sklearn.cluster import DBSCAN
from imutils import build_montages
import numpy as np
import argparse
import pickle
import cv2
import matplotlib.pyplot as plt
import os

# construct the argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-e","--encodings", required=True,
	help="path to serialized db of facial encodings")
ap.add_argument("-j","--jobs",type=int, default=1,
	help="# of parallel jobs to run (-1 will use all CPUs)")
ap.add_argument("-p", "--eps", type=float, default=0.5,
	help="eps of DBSCAN, too big -> one class, too small -> many class")
ap.add_argument("-m", "--min_samples", type=int, default=5,
    help="min samples of DBSCAN")
args = vars(ap.parse_args())

# load the serialized face encodings + bounding box locations from
# disk, then extract the set of encodings so we can cluster them

print("[INFO] loading encodings...")
data = pickle.loads(open(args["encodings"],"rb").read())
print("[INFO] loaded total face count: %d" % len(data))
data = np.array(data)
encodings = np.array([d["encoding"] for d in data])
#np.random.shuffle(encodings)

print(encodings.shape)
#print(encodings[0])
#print(type(encodings))

# cluster the embeddings
print("[INFO] clustering...")
clt = DBSCAN(metric="euclidean", n_jobs=args["jobs"], eps=args["eps"], min_samples=args["min_samples"])
clt.fit(encodings)

plt.scatter(encodings[:, 4], encodings[:, 9], marker='o', c=clt.labels_)
plt.show()

# determine the total number of unique faces found in the dataset
labelIDs = np.unique(clt.labels_)
numUniqueFaces = len(np.where(labelIDs > -1)[0])
print("[INFO] # unique faces : {}".format(numUniqueFaces))

# remove old pic
for num in range(0, 20):
	filename = 'out_%d.jpg' % num
	if os.path.exists(filename):
		os.remove(filename)
		print('file %s deleted' % filename)
	

# loop over the unique face integers
face_id = 0
cluster_face_count = 0
for labelID in labelIDs:
	# find all the indexes into the 'data' array that belong to the
	# current label ID, then randomly sample a maximum of 25 index from the set
	print("[INFO] faces for face ID: {}".format(labelID))
	idxs = np.where(clt.labels_ == labelID)[0]
	print("[INFO] face count: %d, cluster count %d" % (len(idxs), cluster_face_count))
	cluster_face_count = cluster_face_count + len(idxs)
	idxs = np.random.choice(idxs, size=min(25, len(idxs)),
		replace=False)

	# initialize the list of faces to include in the montage
	faces = []
	# loop over the sampled indexes
	for i in idxs:
		# load the input image and extract the face ROI
		image = cv2.imread(data[i]["imagePath"])
		(top, right, bottom, left) = data[i]["loc"]
		face = image[top:bottom, left:right]

		# force resize the face ROI to 96x96 and then add it to the
		# faces montage list
		face = cv2.resize(face, (96,96))
		faces.append(face)

	# create a montage using 96x96 "tiles" with 5 rows and 5 columns
	montage = build_montages(faces, (96,96), (5,5))[0]

	# show the output montage
	title = "Face ID #{}".format(labelID)
	title = "Unknown Faces" if labelID == -1 else title
	#cv2.imshow(title, montage)
	#cv2.waitKey(0)
	cv2.imwrite('out_{}.jpg'.format(face_id), montage)
	face_id += 1

print("[INFO] total cluster_face_count %d" % cluster_face_count)
