from netcdf import netcdf as nc
import matplotlib.pyplot as plt


def draw(filepattern, filename):
    with nc.loader(filepattern) as root:
        data = nc.getvar(root, 'globalradiation')[-1,:,:]
        y, x = data.shape
        plt.figure(figsize=(x/20, y/20))
        img = plt.imshow(data)
        img.set_clim(0, data.max())
        title = root.files[-1].split('/')[-1]
        plt.title(title)
        plt.colorbar()
        plt.axis('off')
        plt.savefig(filename, bbox_inches=0)
    return [filename]
