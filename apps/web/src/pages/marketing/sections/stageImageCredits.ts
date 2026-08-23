/**
 * Attribution for the stage photographs.
 *
 * CC BY requires visible credit, and the planning documents require every
 * outside material to be disclosed regardless of licence. Generated from
 * docs/media-credits.json by scripts/fetch_stage_images.py; edit that, not this.
 */
export interface ImageCredit {
  stage: string;
  title: string;
  creator: string;
  license: string;
  url: string;
}

export const STAGE_IMAGE_CREDITS: readonly ImageCredit[] = [
  {
    stage: 'capture',
    title: 'Camera Lens Photograph - Credit to https://homethods.com/',
    creator: 'homethods',
    license: 'CC BY',
    url: 'https://www.flickr.com/photos/146625745@N08/32534013500',
  },
  {
    stage: 'classify',
    title: 'Colour Pencils-3',
    creator: 'David Blaikie',
    license: 'CC BY',
    url: 'https://www.flickr.com/photos/12568962@N00/3267139809',
  },
  {
    stage: 'contextualize',
    title: 'Free world map pins photo',
    creator: 'Unknown',
    license: 'CC0',
    url: 'https://www.rawpixel.com/image/5926085/photo-image-public-domain-map-free',
  },
  {
    stage: 'review',
    title: 'Manuscript',
    creator: 'sidewalk flying',
    license: 'CC BY',
    url: 'https://www.flickr.com/photos/76994867@N00/5124506505',
  },
  {
    stage: 'report',
    title: 'Print Order Book, Holmes McDougall',
    creator: 'edinburghcityofprint',
    license: 'CC BY',
    url: 'https://www.flickr.com/photos/30239838@N04/4268147953',
  },
];
