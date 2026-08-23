import type { LessonMedia, LessonModule } from './lesson-modules';

/**
 * Public case studies for Lessons.
 *
 * Each case is a documented path through online rooms that later sat beside
 * public violence. The core theme is online radicalization: forums, imageboards,
 * livestreams, and social posts that the public record already named. Speech in
 * those rooms is described as part of the documented path, never as a single
 * comment that produced the attack. Generated stills stand in for places. They
 * are not photographs of the attacks or of anyone involved.
 */

function still(src: string, alt: string, caption: string): LessonMedia {
  return { src, alt, caption };
}

const ISLA_VISTA = still(
  '/media/cases/isla-vista-evening.png',
  'Generated still of a quiet California coastal street at evening. No people are shown.',
  'Generated still of a coastal street at evening. Not a photograph of Isla Vista or of any person.',
);

const QUEBEC = still(
  '/media/cases/quebec-winter.png',
  'Generated still of a snow-covered street and a place of worship at night. No people are shown.',
  'Generated still of a winter street at night. Not a photograph of the 2017 attack, of the building, or of any person.',
);

const TORONTO = still(
  '/media/cases/toronto-street.png',
  'Generated still of a wet downtown street with glass towers in the distance. No people are shown.',
  'Generated still of a city street. Not a photograph of Yonge Street on 23 April 2018 or of any person.',
);

const PITTSBURGH = still(
  '/media/cases/pittsburgh-evening.png',
  'Generated still of a neighborhood street and a place of worship at dusk. No people are shown.',
  'Generated still of a dusk street. Not a photograph of the Tree of Life building or of any person.',
);

const CHRISTCHURCH = still(
  '/media/cases/christchurch-dusk.png',
  'Generated still of a quiet suburban street and a mosque dome at dusk. No people are shown.',
  'Generated still of a quiet street at dusk. Not a photograph of the 2019 attacks, of either mosque, or of any person.',
);

const CALIFORNIA = still(
  '/media/cases/california-evening.png',
  'Generated still of a mosque beside an empty parking lot in evening light. No people are shown.',
  'Generated still of a California evening. Not a photograph of Escondido, Poway, or any person.',
);

const EL_PASO = still(
  '/media/cases/el-paso-dusk.png',
  'Generated still of an empty West Texas parking lot at dusk. No people are shown.',
  'Generated still of a dusk parking lot. Not a photograph of the El Paso attack or of any person.',
);

const PLYMOUTH = still(
  '/media/cases/plymouth-harbour.png',
  'Generated still of a quiet English harbour town at dusk. No people are shown.',
  'Generated still of a coastal town. Not a photograph of Keyham or of any person.',
);

const BUFFALO = still(
  '/media/cases/buffalo-street.png',
  'Generated still of an overcast street and an empty parking lot. No people are shown.',
  'Generated still of a gray street. Not a photograph of the Buffalo attack or of any person.',
);

const HALLE = still(
  '/media/cases/halle-dusk.png',
  'Generated still of a quiet street and a place of worship at dusk. No people are shown.',
  'Generated still of a dusk street. Not a photograph of the 2019 Halle attack, of the synagogue, or of any person.',
);

const BAERUM = still(
  '/media/cases/baerum-evening.png',
  'Generated still of a suburban street and a mosque at evening. No people are shown.',
  'Generated still of a northern evening. Not a photograph of the Al-Noor Islamic Centre, of Bærum, or of any person.',
);

const FINSBURY = still(
  '/media/cases/finsbury-park-night.png',
  'Generated still of a wet London street at night. No people are shown.',
  'Generated still of a night street. Not a photograph of Finsbury Park on 19 June 2017 or of any person.',
);

export const LESSON_CASES: readonly LessonModule[] = [
  {
    id: 'isla-vista',
    number: '01',
    track: 'case',
    place: 'Isla Vista, California',
    dateLabel: '23 May 2014',
    title: 'Elliot Rodger and the incel forums',
    thesis:
      'A young man who had spent years on pickup-artist hate forums and who posted videos on YouTube killed six people in Isla Vista. Later attackers named him in their own posts. The record is about a community that formed online, not about one lonely hour.',
    minutes: 8,
    hero: ISLA_VISTA,
    chapters: [
      {
        id: 'isla-what',
        title: 'What happened',
        visual: 'case-media',
        media: ISLA_VISTA,
        paragraphs: [
          'On 23 May 2014 Elliot Rodger killed six people and injured fourteen in Isla Vista, California, then died by suicide. Santa Barbara County investigators recovered a long autobiographical document and a set of YouTube videos he had uploaded in the days before the attack, including one titled as a retribution address.',
          'The investigation also recovered years of posts on bodybuilding and “pickup artist hate” forums. Those boards were places where men traded contempt for women and for other men, ranked themselves, and treated humiliation as a shared story. Rodger posted there under his own name and under handles the sheriff later tied to him.',
          'This page names him because the conviction of the facts is public and because later attackers cited him in public posts. It does not rank him or treat him as a type that software should hunt.',
        ],
      },
      {
        id: 'isla-online',
        title: 'The online trail',
        paragraphs: [
          'Forum logs and the videos are the trail. They show a person rehearsing grievance in a room that rewarded the rehearsal. Other users argued with him, mocked him, and sometimes agreed. Agreement was not a command. It was a climate. Hoffman, Ware, and Shapiro later described that climate as part of a wider incel ecosystem that outlived Rodger.',
          'YouTube was the broadcast layer. A video can travel farther than a forum thread. A person who never joined PUAHate could still watch the address. That is one reason prevention work watches both closed boards and open platforms: the same story can move from a niche room into a feed.',
          'The honest limit still holds. Most people who read those boards never attack anyone. The puzzle from the research modules applies here. Opinion and action are different pyramids. The forums are still the place where the opinion was practised in public, which is why they belong in any serious account of the case.',
        ],
      },
      {
        id: 'isla-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'Later cases on this list, including Toronto in 2018, named Rodger in posts made just before an attack. That is not a coefficient. It is a documented habit of citation. A community that keeps a “supreme gentleman” on the wall is teaching a story about who counts as a hero.',
          'Monitoring those rooms is not the same as predicting a person. It is closer to reading a weather report: you can see a storm language forming without knowing which house it will hit. Prevention starts with refusing to treat that language as a private diary.',
          'If you need the primary record, the sheriff’s investigative materials and later research reviews are on Sources. If you or someone you know is in crisis, the resource list on the Lessons catalog is the right door.',
        ],
      },
    ],
    sources: [
      {
        id: 'isla-bbc',
        authors: 'BBC News',
        year: 2014,
        title: 'California drive-by shootings: How they unfolded',
        venue: 'BBC News',
        href: 'https://www.bbc.com/news/world-us-canada-27542552',
        note: 'Contemporary reporting of the Isla Vista attacks and of the videos posted beforehand.',
      },
      {
        id: 'isla-hoffman',
        authors: 'Hoffman, B., Ware, J., and Shapiro, E.',
        year: 2020,
        title: 'Assessing the threat of incel violence',
        venue: 'Studies in Conflict and Terrorism',
        doi: '10.1080/1057610X.2020.1751459',
        note: 'A research review of the incel ecosystem after Rodger, including later attackers who cited him.',
      },
    ],
  },
  {
    id: 'quebec',
    number: '02',
    track: 'case',
    place: 'Quebec City, Canada',
    dateLabel: '29 January 2017',
    title: 'Quebec City mosque',
    thesis:
      'A gunman attacked worshippers at the Islamic Cultural Centre of Quebec City after months of reading far-right and anti-Muslim material online. The court record is the source for that online trail.',
    minutes: 8,
    hero: QUEBEC,
    chapters: [
      {
        id: 'quebec-what',
        title: 'What happened',
        visual: 'case-media',
        media: QUEBEC,
        paragraphs: [
          'On 29 January 2017 a gunman entered the Islamic Cultural Centre of Quebec City during evening prayers and opened fire. Six worshippers were killed. Alexandre Bissonnette later pleaded guilty. Canadian courts recorded the facts of the attack and the sentence. In 2022 the Supreme Court of Canada decided R. v. Bissonnette, a case about consecutive sentences that used this attack as its facts.',
          'The people who were killed were there to pray. They are not a datapoint in a hate rate. This page is about the path the convicted attacker walked, including the hours he spent online, because that path is what prevention has to see.',
        ],
      },
      {
        id: 'quebec-online',
        title: 'The online trail',
        paragraphs: [
          'Sentencing material and newsrooms working from it documented that Bissonnette spent long stretches reading far-right, anti-feminist, and anti-Muslim sites and social feeds. Investigators also recorded a history of isolation, firearms practice, and a documented interest in other public attacks.',
          'The feeds did two jobs that forums also do. They offered a story in which Muslims were a threat to a way of life. They offered company for that story, so a person sitting alone could feel like part of a crowd. Neither job is the same as an order to shoot. Both jobs are why those rooms are part of the case.',
          'Anti-Muslim hate online is not a mood. It is a retargeting: a grievance about politics, immigration, or status gets pointed at people walking into a mosque. Borum’s sketch in the syllabus is the same motion, written as a heuristic rather than as this file.',
        ],
      },
      {
        id: 'quebec-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A mosque at prayer is a soft, repeating gathering. Online rooms that treat that gathering as an invasion are practising a target. Watching those rooms is how a later reader sees the practise before the door opens.',
          'Prevention here is not a takedown bot. It is people who can read a feed, name the pattern, and get help to someone who is sliding. The resource list on this catalog includes Canadian desks. The court judgment on Sources is the legal record.',
        ],
      },
    ],
    sources: [
      {
        id: 'quebec-scc',
        authors: 'Supreme Court of Canada',
        year: 2022,
        title: 'R. v. Bissonnette',
        venue: '2022 SCC 23',
        href: 'https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/19491/index.do',
        note: 'The judgment records the facts of the attack as the Court received them.',
      },
      {
        id: 'quebec-cbc',
        authors: 'CBC News',
        year: 2017,
        title: 'Quebec City mosque shooting: what we know',
        venue: 'CBC News',
        href: 'https://www.cbc.ca/news/canada/montreal/quebec-city-mosque-shooting-what-we-know-1.3959582',
        note: 'Contemporary reporting from the days after the attack.',
      },
    ],
  },
  {
    id: 'toronto',
    number: '03',
    track: 'case',
    place: 'Toronto, Canada',
    dateLabel: '23 April 2018',
    title: 'Alec Minassian and the incel rebellion post',
    thesis:
      'Minutes before a van attack on Yonge Street, a Facebook post announced an “incel rebellion” and named Elliot Rodger. The court later heard how incel forums sat on that path.',
    minutes: 8,
    hero: TORONTO,
    chapters: [
      {
        id: 'toronto-what',
        title: 'What happened',
        visual: 'case-media',
        media: TORONTO,
        paragraphs: [
          'On 23 April 2018 Alec Minassian drove a rented van down a sidewalk on Yonge Street in Toronto. Ten people were killed and sixteen were injured. In 2021 the Ontario Superior Court found him guilty of ten counts of first-degree murder and sixteen of attempted murder. The reasons for judgment are public.',
          'Shortly before the attack he posted on Facebook that an incel rebellion had begun and named Elliot Rodger as the figure to hail. The post is part of the court record. This page does not reproduce the rest of that wording.',
        ],
      },
      {
        id: 'toronto-online',
        title: 'The online trail',
        paragraphs: [
          'The trial heard that Minassian had spent time on incel boards and that he understood the Rodger story as a script he could join. Facebook was the last surface: a public announcement, not a private diary. A platform that large can carry a niche ideology into a place families scroll at lunch.',
          'Incel rooms recycle a simple ranking. Some men are owed sex. Women and successful men are the ones who withheld it. Violence is framed as a revolt. Rodger is the saint of that revolt. Once a person accepts the ranking, every later slight reads as proof. That is radicalization as a story, practised in comments, not as a secret lodge.',
          'Again the two pyramids apply. Most readers of those boards never drive a van onto a sidewalk. The board is still where the story was kept warm. That is the monitoring problem: you are watching a story that is cheap to copy and expensive to ignore.',
        ],
      },
      {
        id: 'toronto-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A Facebook post that names a previous attacker is a flare. It tells you the person has entered a canon. Prevention work that never reads social posts will miss the flare. Work that only reads the flare, and never the years of board time behind it, will treat the last hour as the whole path.',
          'Canadian crisis and community links sit in the resource list. The CanLII judgment on Sources is the court record, not a recap thread.',
        ],
      },
    ],
    sources: [
      {
        id: 'toronto-canlii',
        authors: 'Ontario Superior Court of Justice',
        year: 2021,
        title: 'R. v. Minassian',
        venue: '2021 ONSC 1257',
        href: 'https://www.canlii.org/en/on/onsc/doc/2021/2021onsc1257/2021onsc1257.html',
        note: 'Reasons for judgment, including the Facebook post and the incel evidence the Court accepted.',
      },
      {
        id: 'toronto-cbc',
        authors: 'CBC News',
        year: 2018,
        title: 'What we know about the Toronto van attack',
        venue: 'CBC News',
        href: 'https://www.cbc.ca/news/canada/toronto/toronto-van-attack-what-we-know-1.4633402',
        note: 'Contemporary reporting of the attack and of the Facebook post.',
      },
    ],
  },
  {
    id: 'pittsburgh',
    number: '04',
    track: 'case',
    place: 'Pittsburgh, United States',
    dateLabel: '27 October 2018',
    title: 'Tree of Life and Gab',
    thesis:
      'Eleven worshippers were killed at the Tree of Life synagogue after the attacker posted on Gab, a network that marketed itself as a home for speech other platforms had refused. The federal case is the source.',
    minutes: 7,
    hero: PITTSBURGH,
    chapters: [
      {
        id: 'pittsburgh-what',
        title: 'What happened',
        visual: 'case-media',
        media: PITTSBURGH,
        paragraphs: [
          'On 27 October 2018 Robert Bowers attacked the Tree of Life synagogue in Pittsburgh during Shabbat services. Eleven people were killed. A federal jury later convicted him. In 2023 he was sentenced to death. The Department of Justice published the sentencing announcement.',
          'This case is not an anti-Muslim attack. It is on this list because the path ran through an online network that gathered people around conspiracy and hate, then sat beside a massacre in a house of worship. The pattern is the same motion: a feed retargets a grievance onto a congregation.',
        ],
      },
      {
        id: 'pittsburgh-online',
        title: 'The online trail',
        paragraphs: [
          'Prosecutors showed that Bowers posted on Gab shortly before the attack, including language about a Jewish refugee-resettlement organisation. Gab had marketed itself as a refuge after other platforms enforced rules. A refuge of that kind can become a hothouse: the people who remain are the ones who want the speech that was refused elsewhere.',
          'That is a monitoring lesson. Radicalization is not only a journey into a darker site. It can be a journey onto a site that promises never to push back. The feed then does the rest: repetition, agreement, a sense that “everyone here already knows.”',
        ],
      },
      {
        id: 'pittsburgh-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'Houses of worship are scheduled and public. Online rooms that name them as enemies are selecting a time and a door. Reading those rooms is how a later prevention effort sees the selection while it is still words.',
          'The DOJ sentencing release on Sources is the federal record. It does not replace the families’ own accounts.',
        ],
      },
    ],
    sources: [
      {
        id: 'pittsburgh-doj',
        authors: 'United States Department of Justice',
        year: 2023,
        title: 'Robert Bowers sentenced to death for Tree of Life synagogue attack',
        venue: 'Department of Justice',
        href: 'https://www.justice.gov/opa/pr/robert-bowers-sentenced-death-after-jury-finds-him-eligible-capital-punishment-tree-life',
        note: 'Federal sentencing announcement. Read the filing, not a recap thread.',
      },
    ],
  },
  {
    id: 'christchurch',
    number: '05',
    track: 'case',
    place: 'Christchurch, New Zealand',
    dateLabel: '15 March 2019',
    title: 'Christchurch masjidain',
    thesis:
      'The Royal Commission recorded two consecutive attacks on mosques and years on extreme imageboards, plus a livestream meant to be copied. The inquiry is the source. A livestream is not a lesson, and a manifesto is not cited here.',
    minutes: 9,
    hero: CHRISTCHURCH,
    chapters: [
      {
        id: 'christchurch-what',
        title: 'What the inquiry recorded',
        visual: 'case-media',
        media: CHRISTCHURCH,
        paragraphs: [
          'On 15 March 2019 a gunman attacked Masjid an-Nur and then the Linwood Islamic Centre in Christchurch. Fifty-one people were killed. Brenton Tarrant was later convicted. New Zealand established a Royal Commission of Inquiry into the terrorist attack on Christchurch masjidain. The Commission’s report, Ko tō tātou kāinga tēnei, is the account this page follows.',
          'This page does not reproduce the livestream, the manifesto, or a target list. Those choices are for families, courts, and the inquiry.',
        ],
      },
      {
        id: 'christchurch-online',
        title: 'Imageboards and a livestream',
        paragraphs: [
          'The Commission recorded that the attacker spent years on extreme imageboards, including 4chan and later 8chan, and that he published a document and a livestream intended to be copied. Those board names stay in the prose. This product does not link to them.',
          'An imageboard is built for speed and anonymity. A joke, a slur, and a plan can share a thread. The livestream then turned the attack into a file other rooms could replay. Copy-language showed up in later public cases, including a mosque fire in California nine days later and a shooting in El Paso that summer. A sequence is a sequence. It is still the clearest picture we have of how one room’s aesthetic can travel.',
          'Ribeiro and others, in the syllabus, are the right caution beside this file: migration toward more extreme spaces can coincide with later harm without proving that the last thread produced it. The boards remain the place the inquiry named.',
        ],
      },
      {
        id: 'christchurch-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'If a later attacker can watch a previous one as entertainment, the room is doing recruitment without a recruiter. Prevention that only watches “known groups” will miss a board that treats massacre as a meme.',
          'Open the Royal Commission site from Sources. If you need a crisis line, the Resources list on the Lessons catalog is the right door.',
        ],
      },
    ],
    sources: [
      {
        id: 'christchurch-rcoi',
        authors: 'Royal Commission of Inquiry',
        year: 2020,
        title:
          'Ko tō tātou kāinga tēnei: Report of the Royal Commission of Inquiry into the terrorist attack on Christchurch masjidain on 15 March 2019',
        venue: 'New Zealand Government',
        href: 'https://christchurchattack.royalcommission.nz/',
        note: 'The inquiry is the source of record. Do not substitute a social-media recap for it.',
      },
    ],
  },
  {
    id: 'california',
    number: '06',
    track: 'case',
    place: 'Escondido and Poway, California',
    dateLabel: 'March and April 2019',
    title: 'Escondido mosque fire and Poway',
    thesis:
      'Nine days after Christchurch, an arson attack was set at a mosque in Escondido. Weeks later the same person attacked a synagogue in Poway. Federal filings described a post on an imageboard that referred to Christchurch.',
    minutes: 8,
    hero: CALIFORNIA,
    chapters: [
      {
        id: 'california-what',
        title: 'What happened',
        visual: 'case-media',
        media: CALIFORNIA,
        paragraphs: [
          'On 24 March 2019 an arson attack was set at the Dar-ul-Arqam mosque in Escondido, California. On 27 April 2019 John Earnest attacked the Chabad of Poway synagogue. One worshipper was killed. Federal court records later tied both crimes to the same person. This page is about the documented events, not a person-level dossier.',
          'The mosque fire is the anti-Muslim targeting in this pair. The synagogue attack is a separate crime against a different community. Collapsing both into one “hate” count would hide who was targeted. Both sit on a path the filings said ran through an imageboard.',
        ],
      },
      {
        id: 'california-online',
        title: 'The online trail',
        paragraphs: [
          'Public filings described a post and graffiti that referred to Christchurch. That is a documented inscription, not a measurement that Christchurch comments produced the fire. The honest sentence is the one the syllabus uses: the events sit on a timeline, and the board is the room the filings named.',
          'Copying is itself a form of radicalization. A person who treats a previous livestream as a template is joining a canon, the same way Minassian joined Rodger. The platform that hosts the canon, even for an hour, is part of the path that has to be watched.',
        ],
      },
      {
        id: 'california-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'Two houses of worship, two communities, one online habit: cite the last attack, then try the next door. Prevention that reads those citations as noise will keep being surprised. Prevention that reads them as a pattern can warn a congregation and a platform at the same time.',
          'The Department of Justice sentencing material on Sources is the federal record.',
        ],
      },
    ],
    sources: [
      {
        id: 'california-doj',
        authors: 'United States Department of Justice',
        year: 2021,
        title:
          'California man sentenced for federal hate crimes in mosque arson and synagogue shooting',
        venue: 'Department of Justice',
        href: 'https://www.justice.gov/usao-sdca/pr/escondido-man-sentenced-more-17-years-federal-hate-crime-charges',
        note: 'Federal sentencing material for the 2019 California pair.',
      },
    ],
  },
  {
    id: 'el-paso',
    number: '07',
    track: 'case',
    place: 'El Paso, Texas',
    dateLabel: '3 August 2019',
    title: 'Patrick Crusius and the El Paso posting',
    thesis:
      'A gunman attacked shoppers at a Walmart in El Paso after posting a document on 8chan. Federal prosecutors said he had written about a Hispanic “invasion.” Twenty-three people were killed.',
    minutes: 8,
    hero: EL_PASO,
    chapters: [
      {
        id: 'elpaso-what',
        title: 'What happened',
        visual: 'case-media',
        media: EL_PASO,
        paragraphs: [
          'On 3 August 2019 Patrick Crusius attacked a Walmart in El Paso, Texas. Twenty-three people were killed. Many of the dead were Hispanic. In 2023 a federal court sentenced him to 90 consecutive life sentences. The Department of Justice published the announcement.',
          'Prosecutors said he had posted a document on 8chan shortly before the attack. This page does not quote it. The posting is the online fact that belongs here: a manifesto dropped into a board that had already hosted Christchurch copy.',
        ],
      },
      {
        id: 'elpaso-online',
        title: 'The online trail',
        paragraphs: [
          '8chan, later 8kun, was an imageboard that other attackers had already used as a drop box. A person could write a racial story, post it, then go to a car park. The board’s culture treated that sequence as a performance. That is radicalization as an audience problem: the writer wants the room to see the post land.',
          'The “invasion” story is an old political claim pointed at shoppers. Online rooms keep the claim hot and give it a uniform. A person who arrives with a vague anger can leave with a target list that looks, to them, like common sense.',
        ],
      },
      {
        id: 'elpaso-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A grocery store on a Saturday is ordinary life. A board that calls that life an invasion is selecting the ordinary as the battlefield. Watching the board is how you see the selection while it is still a paragraph.',
          'The DOJ sentencing release on Sources is the federal record.',
        ],
      },
    ],
    sources: [
      {
        id: 'elpaso-doj',
        authors: 'United States Department of Justice',
        year: 2023,
        title: 'Texas man sentenced to 90 consecutive life sentences for El Paso mass shooting',
        venue: 'Department of Justice',
        href: 'https://www.justice.gov/opa/pr/texas-man-sentenced-90-consecutive-life-sentences-committing-hate-crime-and-firearm',
        note: 'Federal sentencing announcement, including the online posting the government described.',
      },
    ],
  },
  {
    id: 'plymouth',
    number: '08',
    track: 'case',
    place: 'Plymouth, United Kingdom',
    dateLabel: '12 August 2021',
    title: 'Jake Davison and incel material',
    thesis:
      'A shooting in Keyham, Plymouth, killed five people. The inquest and later reporting documented the shooter’s use of incel forums and related social posts. The path ran through rooms that recycle the Rodger story in a British town.',
    minutes: 7,
    hero: PLYMOUTH,
    chapters: [
      {
        id: 'plymouth-what',
        title: 'What happened',
        visual: 'case-media',
        media: PLYMOUTH,
        paragraphs: [
          'On 12 August 2021 Jake Davison shot and killed five people in Keyham, Plymouth, including his mother, then died by suicide. An inquest examined how he had obtained a shotgun licence, how mental-health services had met him, and what he had been reading and posting online.',
          'Reporting of the inquest, including BBC coverage, documented incel material on his devices and social accounts: forums and posts that framed women as the source of his humiliation. That material sits beside, and does not replace, the failures of licensing and care the inquest also named.',
        ],
      },
      {
        id: 'plymouth-online',
        title: 'The online trail',
        paragraphs: [
          'Incel rooms did not stay in California or Toronto. A British man could join the same canon from a bedroom in Plymouth. The story travels because the platforms are global and the ranking is simple. Once it is installed, a local slight reads like a chapter of Rodger’s document.',
          'Social posts and forum history are not a diagnosis. They are a record of the company a person kept. When that company keeps a massacre on a pedestal, the company is part of the risk a later inquest will have to describe.',
        ],
      },
      {
        id: 'plymouth-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'Licensing, mental-health care, and online rooms are different levers. An inquest that names all three is refusing a single-rung story. Prevention that only watches forums will miss a licence. Prevention that only watches licences will miss a forum. The case is here so the forum lever stays visible.',
          'Samaritans and other UK lines sit in the resource list. BBC inquest reporting is on Sources.',
        ],
      },
    ],
    sources: [
      {
        id: 'plymouth-bbc',
        authors: 'BBC News',
        year: 2023,
        title: 'Plymouth shooting: Inquest findings into the Keyham deaths',
        venue: 'BBC News',
        href: 'https://www.bbc.com/news/uk-england-devon-64623421',
        note: 'Reporting of the inquest, including online incel material the inquest heard.',
      },
    ],
  },
  {
    id: 'buffalo',
    number: '09',
    track: 'case',
    place: 'Buffalo, New York',
    dateLabel: '14 May 2022',
    title: 'Payton Gendron, 4chan, and Discord',
    thesis:
      'Ten people were killed at a supermarket in Buffalo. Court and reporting described years on 4chan, a Discord diary, and a livestream. The federal and New York cases are the source.',
    minutes: 8,
    hero: BUFFALO,
    chapters: [
      {
        id: 'buffalo-what',
        title: 'What happened',
        visual: 'case-media',
        media: BUFFALO,
        paragraphs: [
          'On 14 May 2022 Payton Gendron attacked a Tops supermarket in Buffalo, New York. Ten people were killed. The dead were Black. He later pleaded guilty in state court and was sentenced to life. Federal hate-crime charges followed. The Department of Justice published those announcements.',
          'Investigators described a written plan, a livestream, and a long period of posting and reading on imageboards and on Discord. This page does not quote the document or the stream.',
        ],
      },
      {
        id: 'buffalo-online',
        title: 'The online trail',
        paragraphs: [
          '4chan supplied the racial story and the joke-as-armor. Discord supplied a diary that could be kept in a channel. The livestream supplied an audience. Three surfaces, one path: a person moves from reading, to writing for a small room, to performing for anyone who can find the link.',
          'That ladder is still not a fate. It is a set of rooms that make the next step feel ordinary. Monitoring has to see the rooms as a sequence, not as three unrelated products. A later reader who only checks one platform will miss the diary, or the stream, or the board that taught the joke.',
        ],
      },
      {
        id: 'buffalo-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A supermarket in a Black neighborhood is ordinary life. A board that calls that life a replacement is selecting the ordinary, again. The Christchurch, El Paso, and Buffalo files share that selection. The shared online habit is why they sit on one list.',
          'The DOJ materials on Sources are the federal record. New York’s case is the state record.',
        ],
      },
    ],
    sources: [
      {
        id: 'buffalo-doj',
        authors: 'United States Department of Justice',
        year: 2023,
        title: 'Payton Gendron sentenced to life in prison for hate crimes in Buffalo',
        venue: 'Department of Justice',
        href: 'https://www.justice.gov/opa/pr/payton-gendron-sentenced-life-prison-hate-crimes-and-firearms-offenses-may-2022',
        note: 'Federal sentencing announcement, including the online trail the government described.',
      },
    ],
  },
  {
    id: 'halle',
    number: '10',
    track: 'case',
    place: 'Halle, Germany',
    dateLabel: '9 October 2019',
    title: 'Stephan Balliet and the livestreamed attack',
    thesis:
      'A gunman tried to enter a synagogue in Halle on Yom Kippur, then killed two people nearby. He livestreamed the attempt. The German court record, as later reported, placed the path beside rooms that already treated Christchurch as a script.',
    minutes: 8,
    hero: HALLE,
    chapters: [
      {
        id: 'halle-what',
        title: 'What happened',
        visual: 'case-media',
        media: HALLE,
        paragraphs: [
          'On 9 October 2019, Yom Kippur, Stephan Balliet tried to force his way into the synagogue in Halle, Germany. A locked door kept him out. He then killed two people nearby, including a man in a kebab shop, and wounded others. In December 2020 a German court sentenced him to life. BBC News published the sentencing report.',
          'He livestreamed the attempt. This page does not show or quote the stream. The stream is the online fact that belongs here: an attack staged so a room could watch it in real time.',
        ],
      },
      {
        id: 'halle-online',
        title: 'The online trail',
        paragraphs: [
          'The sentencing report, and later coverage of the trial, described a livestream aimed at an online audience. Those rooms had already treated the Christchurch livestream as a model. A person could watch a massacre, write a follow-up, then turn a camera on himself. That is radicalization as an audience problem: the writer wants the room to see the attempt land.',
          'The antisemitic story and the anti-Muslim story sat in the same canon. A kebab shop after a failed synagogue entry is not a second plot. It is the same ranking of who counts as a target. The rooms keep that ranking hot and give it a uniform.',
        ],
      },
      {
        id: 'halle-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A livestream turns a street into a stage. A board that cheers the stage is selecting ordinary worship as the battlefield. Watching the board is how you see that selection while it is still a paragraph and a joke.',
          'The BBC sentencing report on Sources is the public court record this page relies on. It is not a finding that one post produced the attack.',
        ],
      },
    ],
    sources: [
      {
        id: 'halle-bbc',
        authors: 'BBC News',
        year: 2020,
        title: 'Halle synagogue attack: Germany far-right gunman jailed for life',
        venue: 'BBC News',
        href: 'https://www.bbc.com/news/world-europe-55395682',
        note: 'Sentencing report, including the livestream and the failed entry on Yom Kippur.',
      },
    ],
  },
  {
    id: 'baerum',
    number: '11',
    track: 'case',
    place: 'Bærum, Norway',
    dateLabel: '10 August 2019',
    title: 'Philip Manshaus and the Al-Noor mosque',
    thesis:
      'A gunman attacked the Al-Noor Islamic Centre in Bærum after killing his stepsister at home. Worshippers stopped him inside the mosque. The court record, as later reported, described neo-Nazi websites and a citation of the Christchurch attacker.',
    minutes: 7,
    hero: BAERUM,
    chapters: [
      {
        id: 'baerum-what',
        title: 'What happened',
        visual: 'case-media',
        media: BAERUM,
        paragraphs: [
          'On 10 August 2019 Philip Manshaus killed his stepsister at home, then drove to the Al-Noor Islamic Centre in Bærum, near Oslo. He fired inside the mosque. Worshippers overpowered him before he could kill anyone there. A Norwegian court later convicted him. BBC News reported both the attack and the later sentence.',
          'This page names him because the conviction is public. It does not rank him or treat him as a type that software should hunt.',
        ],
      },
      {
        id: 'baerum-online',
        title: 'The online trail',
        paragraphs: [
          'The sentencing court, as BBC News reported it, described visits to neo-Nazi websites, including pages that called for a race-based civil war. Reporting of the case also recorded that he had named Brenton Tarrant, the Christchurch attacker. Naming is not a coefficient. It is a documented habit of citation: a later writer treating an earlier massacre as a chapter to continue.',
          'The Christchurch livestream had already shown a mosque as a stage. A person in a Norwegian suburb could join that canon without ever standing in Christchurch. The rooms are global. The target list they keep is local worship on an ordinary day.',
        ],
      },
      {
        id: 'baerum-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A mosque on a Saturday is ordinary life. A board that treats a livestreamed massacre as homework is selecting that life as the next scene. The worshippers who stopped him are part of the public record. So is the board that had already written the scene.',
          'BBC reporting on Sources is the public trail this page uses. A documented timeline is not proof that one post produced the attack.',
        ],
      },
    ],
    sources: [
      {
        id: 'baerum-bbc',
        authors: 'BBC News',
        year: 2020,
        title: 'Norway court jails mosque gunman Manshaus for 21 years',
        venue: 'BBC News',
        href: 'https://www.bbc.com/news/world-europe-53006164',
        note: 'Sentencing report for the Bærum mosque attack and the killing that preceded it.',
      },
    ],
  },
  {
    id: 'finsbury-park',
    number: '12',
    track: 'case',
    place: 'Finsbury Park, London',
    dateLabel: '19 June 2017',
    title: 'Darren Osborne and the van attack',
    thesis:
      'A hired van was driven into Muslim worshippers near Finsbury Park Mosque. One man died. The trial documented days of far-right and anti-Muslim material online, and a plan formed in that climate rather than in a single hour.',
    minutes: 7,
    hero: FINSBURY,
    chapters: [
      {
        id: 'finsbury-what',
        title: 'What happened',
        visual: 'case-media',
        media: FINSBURY,
        paragraphs: [
          'In the early hours of 19 June 2017 Darren Osborne drove a hired van into people who had been at night prayers near Finsbury Park Mosque in London. Makram Ali died. Others were injured. In 2018 Woolwich Crown Court convicted Osborne of murder and attempted murder. BBC News reported the trial and the sentence.',
          'The court heard that he had hired the van after travelling from Cardiff, and that he had looked for a mosque as a target. This page does not reconstruct a minute-by-minute hunt. It records that the choice of worshippers was deliberate and that the court treated it as a terrorist attack.',
        ],
      },
      {
        id: 'finsbury-online',
        title: 'The online trail',
        paragraphs: [
          'The trial documented a short, intense period of far-right and anti-Muslim material: videos, posts, and pages that framed Muslims as a threat after other attacks in the United Kingdom that year. The material sat on ordinary social platforms, not only on closed boards. A person could move from a feed to a van hire without joining an imageboard.',
          'That is a different door from Halle or Bærum, and the same lesson. Radicalization of opinion can happen in a living room with a phone. Most people who watch those videos never attack anyone. The feed is still the place where the opinion was practised in public, which is why it belongs in the account.',
        ],
      },
      {
        id: 'finsbury-why',
        title: 'Why the rooms matter',
        paragraphs: [
          'A pavement outside a mosque after night prayers is ordinary life. A feed that treats that life as an enemy is selecting the ordinary, again. Watching the feed is how you see the selection while it is still a share and a comment.',
          'BBC trial reporting on Sources is the public court record. Samaritans and other UK lines sit in the resource list.',
        ],
      },
    ],
    sources: [
      {
        id: 'finsbury-bbc',
        authors: 'BBC News',
        year: 2018,
        title: 'Finsbury Park attacker Darren Osborne jailed for minimum of 43 years',
        venue: 'BBC News',
        href: 'https://www.bbc.com/news/uk-42920929',
        note: 'Sentencing report for the Finsbury Park van attack, including the online material the trial heard.',
      },
    ],
  },
];
