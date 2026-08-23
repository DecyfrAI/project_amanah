/**
 * The eight-module syllabus for Lessons.
 *
 * Each module is published research, paraphrased for a short reader. None of
 * this is an Amanah finding, a classification of a comment, or a claim that
 * speech caused an attack. Citations live on the last page of every module.
 */

export interface LessonSource {
  readonly id: string;
  readonly authors: string;
  readonly year: number;
  readonly title: string;
  readonly venue: string;
  readonly doi?: string;
  /** Stable open copy when it is not the DOI landing page. */
  readonly href?: string;
  readonly note?: string;
}

export interface LessonMedia {
  readonly src: string;
  readonly alt: string;
  readonly caption: string;
}

export interface LessonChapter {
  readonly id: string;
  readonly title: string;
  readonly paragraphs: readonly string[];
  /** Optional figure rendered on this page, never instead of the prose. */
  readonly visual?: 'mindset-stages' | 'isolation-room' | 'case-media';
  readonly media?: LessonMedia;
}

export interface LessonModule {
  readonly id: string;
  readonly number: string;
  readonly title: string;
  readonly thesis: string;
  readonly minutes: number;
  readonly chapters: readonly LessonChapter[];
  readonly sources: readonly LessonSource[];
  /** Public case studies sit beside the numbered syllabus, not inside it. */
  readonly track?: 'syllabus' | 'case';
  readonly place?: string;
  readonly dateLabel?: string;
  readonly hero?: LessonMedia;
}

export const LESSON_RESEARCH_NOTE =
  'This module summarizes published research. It is not an Amanah finding, and it does not classify any comment.';

export const LESSON_CASE_NOTE =
  'This case study summarizes public inquiries, court records, and reporting about time spent in online rooms before later violence. It is for education. A documented timeline is not proof that one post produced the attack.';

export const LESSON_MODULES: readonly LessonModule[] = [
  {
    id: '01',
    number: '01',
    title: 'Opinion is not action',
    thesis:
      'Radicalization of opinion and radicalization of action are different pyramids. Most people who hold a radical view never act on it.',
    minutes: 9,
    chapters: [
      {
        id: '01-two-pyramids',
        title: 'Two pyramids, not one ladder',
        paragraphs: [
          'A common picture of radicalization is a single staircase: a person climbs from sympathy, to justification, to illegal protest, to violence. McCauley and Moskalenko (2017) argue that picture mixes two things that need separate accounts. One pyramid is opinion. The other is action.',
          'On the opinion pyramid, people range from those who reject a political violence justification, through those who see it as sometimes defensible, to a smaller set who treat it as a personal duty. On the action pyramid, people range from inert, through legal activism and illegal protest, to a still smaller set who use violence. The two pyramids are not stacked. A person can sit high on one and low on the other.',
          'The 2017 paper is a review of that distinction, not a dataset from this product. The DOI is 10.1037/amp0000062. An author manuscript is also on the Bryn Mawr repository.',
        ],
      },
      {
        id: '01-most-never-act',
        title: 'Most radical opinion never becomes action',
        paragraphs: [
          'The warrant for two pyramids is empirical and old. Attitude research has long shown that extreme views are a weak predictor of extreme behaviour. McCauley and Moskalenko put a sharper point on it for political violence: the large majority of people who endorse a radical justification never join an illegal act.',
          'The reverse also happens. People join a violent group, or a riot, or a plot, without first climbing an opinion staircase. Group bonds, love, fear, and status can move action while opinion stays mixed or even thin. Treating every harsh comment as a rung toward violence therefore overcounts the threat and undercounts other paths.',
          'None of that says a comment is harmless. It says a comment is a comment. Opinion and action have to be measured separately, with their own denominators.',
        ],
      },
      {
        id: '01-puzzle',
        title: 'The puzzle is not a missing step',
        paragraphs: [
          'Hafez and Mullins (2015) call the same problem a puzzle rather than a pathway. After reviewing empirical work on homegrown extremism, they argue that no single profile, ideology, or sequence explains who moves into violence. Grievance, networks, enabling environments, and ideology appear again and again, but they combine in different orders.',
          'A puzzle framing is useful because it resists the temptation to treat the last visible remark as the missing piece. If the pieces can be assembled in more than one way, a staircase model will keep finding exceptions and then quietly ignore them.',
          'Hafez and Mullins are synthesizing other studies, not estimating a rate for any platform. Their DOI is 10.1080/1057610X.2015.1051375. Read them as a warning about overfitted stories, not as a substitute for a scoped count.',
        ],
      },
      {
        id: '01-what-for',
        title: 'What the distinction is for',
        paragraphs: [
          'Separating opinion from action is a research discipline. It keeps a study from treating every sympathizer as a recruit, and it keeps a prevention program from treating every recruit as someone who first needed a new idea.',
          'It is also a measurement discipline. A count of hostile posts is a count of posts. A count of assaults is a count of assaults. Placing them in the same window can be informative. Collapsing them into one ladder is not.',
          'Later modules stay inside this limit. They describe mechanisms, rooms, and methods. They do not promote anyone from a sentence to a suspect.',
        ],
      },
    ],
    sources: [
      {
        id: 'mccauley-moskalenko-2017',
        authors: 'Clark McCauley and Sophia Moskalenko',
        year: 2017,
        title: 'Understanding political radicalization: The two-pyramids model',
        venue: 'American Psychologist, 72(3), 205-216',
        doi: '10.1037/amp0000062',
        href: 'https://repository.brynmawr.edu/cgi/viewcontent.cgi?article=1059&context=psych_pubs',
        note: 'Author manuscript on the Bryn Mawr repository. The DOI is the version of record.',
      },
      {
        id: 'hafez-mullins-2015',
        authors: 'Mohammed Hafez and Creighton Mullins',
        year: 2015,
        title:
          'The radicalization puzzle: A theoretical synthesis of empirical approaches to homegrown extremism',
        venue: 'Studies in Conflict and Terrorism, 38(11), 958-975',
        doi: '10.1080/1057610X.2015.1051375',
      },
    ],
  },
  {
    id: '02',
    number: '02',
    title: 'Many doors, not one staircase',
    thesis:
      'People enter political violence through several mechanisms. A single stage model is a sketch, not a map of every case.',
    minutes: 10,
    chapters: [
      {
        id: '02-mechanisms',
        title: 'Mechanisms, not a stage model',
        paragraphs: [
          'If opinion and action are different pyramids, the next question is how anyone moves at all. McCauley and Moskalenko (2008) answer with mechanisms: recurring social and psychological processes that can radicalize a person or a group. Their paper lists twelve, split between individual and group levels.',
          'A mechanism is not a stage. It does not have to arrive in order, and a person does not have to pass through all of them. Two people can reach a similar act through different combinations. That is the point of a mechanisms list. It is a set of doors, not a staircase.',
          'The 2008 paper is in Terrorism and Political Violence. The DOI is 10.1080/09546550802073367. It is a theoretical inventory grounded in cases, not a prevalence estimate for any current platform.',
        ],
      },
      {
        id: '02-individual',
        title: 'Doors that open for a person',
        paragraphs: [
          'At the individual level, the 2008 inventory includes personal victimization, a political grievance, a slippery-slope joining of a radical group, joining through love or friendship, and extremity shifts inside a like-minded circle. Each can move opinion, action, or both. None requires the others.',
          'Personal victimization and political grievance are easy to over-read. Many people are harmed or angered and never enter illegal action. The mechanism is a possible door, not a prediction. The same is true of love: people have followed partners into groups whose ideology they barely held.',
          'The inventory is also a caution against single-cause stories. If several doors exist, a biography that features only the last visible insult is an incomplete biography.',
        ],
      },
      {
        id: '02-group',
        title: 'Doors that open for a group',
        paragraphs: [
          'At the group level, isolation, competition with the state, competition with rival groups, and within-group fission can push a circle toward more extreme tactics. Isolation matters because a room that talks only to itself can treat cruelty as ordinary work.',
          'Jujitsu politics is another group mechanism in the 2008 list: a movement invites a harsh response so that bystanders swing toward the movement. That is a claim about strategy, not a claim that any one protest caused a later attack.',
          'Group mechanisms are easy to miss if a study only codes individual posts. A thread can radicalize a room even when no single author looks like a recruit.',
        ],
      },
      {
        id: '02-borum-review',
        title: 'A review, and a sketch that stayed too famous',
        paragraphs: [
          'Borum (2011) surveyed social-science theories of radicalization into violent extremism and found the same plurality. Social movement theory, social psychology, conversion research, and stage models all describe pieces. None owns the phenomenon.',
          'Borum also notes that his own 2003 four-stage sketch, written for investigators, is a heuristic. It can help a reader notice how a grievance is retargeted. It is not a validated staircase, and it was never meant as a screen for every poster.',
          'Module 03 sits with that 2003 sketch in more detail. The point here is simpler: a widely taught diagram is still a sketch. The 2011 review is open in the Journal of Strategic Security.',
        ],
      },
    ],
    sources: [
      {
        id: 'mccauley-moskalenko-2008',
        authors: 'Clark McCauley and Sophia Moskalenko',
        year: 2008,
        title: 'Mechanisms of political radicalization: Pathways toward terrorism',
        venue: 'Terrorism and Political Violence, 20(3), 415-433',
        doi: '10.1080/09546550802073367',
      },
      {
        id: 'borum-2011',
        authors: 'Randy Borum',
        year: 2011,
        title: 'Radicalization into violent extremism I: A review of social science theories',
        venue: 'Journal of Strategic Security, 4(4), 7-36',
        doi: '10.5038/1944-0472.4.4.1',
        href: 'https://digitalcommons.usf.edu/jss/vol4/iss4/2/',
      },
    ],
  },
  {
    id: '03',
    number: '03',
    title: 'How a grievance becomes a target',
    thesis:
      'Borum’s 2003 sketch and Bandura’s moral disengagement describe how some people move from a wrong to a person they no longer owe care.',
    minutes: 10,
    chapters: [
      {
        id: '03-heuristic',
        title: 'A heuristic, not a law',
        paragraphs: [
          'In 2003, Randy Borum published a short piece in the FBI Law Enforcement Bulletin that investigators still meet as a four-stage diagram. It describes how some people move from naming a grievance to placing a target outside ordinary moral concern.',
          'Borum later called the diagram a heuristic. It is a way to notice a story changing shape. It is not a claim that every angry person follows the sequence, and it is not a test that can be run on a comment feed.',
          'An open copy sits on the University of South Florida repository. The original appeared in the July 2003 bulletin. Use either as the source of the sketch, not as a finding about anyone on a dashboard.',
        ],
      },
      {
        id: '03-four-movements',
        title: 'Four movements in the sketch',
        paragraphs: [
          'The first movement names a wrong: it is not right. The feeling can be inherited, taught, or earned. A grievance is not yet a target.',
          'The second recasts the wrong as an injustice done to a group the person identifies with: it is not fair. The third assigns blame to a people, a faith, or a type of stranger: it is your fault. The fourth places that target outside ordinary moral concern: you are evil.',
          'The figure below is the same sketch, written for a reader rather than for an investigator. Click a stage to sit with it. Colour darkens along the sequence, but each stage also has a number, a name, and a quote, because colour is never the only cue.',
        ],
        visual: 'mindset-stages',
      },
      {
        id: '03-bandura',
        title: 'How care gets switched off',
        paragraphs: [
          'Bandura’s work on moral disengagement asks a neighbouring question: how do people who still think of themselves as decent come to accept harm? The mechanisms include moral justification, euphemism, advantageous comparison, displacement and diffusion of responsibility, minimizing consequences, dehumanization, and blaming the victim.',
          'Dehumanization and blame are the closest cousins of Borum’s fourth stage. A target who is no longer seen as a person, or who is said to have invited the harm, is easier to cheer against. The other mechanisms matter too. A room that calls cruelty “just asking questions” is already doing euphemistic work.',
          'Bandura (1999) is a review of those mechanisms in the Personality and Social Psychology Review. The DOI is 10.1207/s15327957pspr0303_3. It is a theory of self-exoneration, not a claim that any one post caused an assault.',
        ],
      },
      {
        id: '03-limits',
        title: 'What the model does not say',
        paragraphs: [
          'The sketch does not say a remark produced an attack. It does not say every poster who uses collective blame is on a path. It does not license a person-level score.',
          'McCauley and Moskalenko’s 2008 mechanisms sit beside it, not underneath it. Group isolation and polarization can harden a room without any one member walking Borum’s four steps in order.',
          'Keep the diagram as a published account of how a grievance can be retargeted. Do not keep it as a verdict.',
        ],
      },
    ],
    sources: [
      {
        id: 'borum-2003',
        authors: 'Randy Borum',
        year: 2003,
        title: 'Understanding the terrorist mindset',
        venue: 'FBI Law Enforcement Bulletin, 72(7), 7-10',
        href: 'https://digitalcommons.usf.edu/mhlp_facpub/568/',
        note: 'Open copy on the University of South Florida repository. The 2003 bulletin piece is the original sketch.',
      },
      {
        id: 'bandura-1999',
        authors: 'Albert Bandura',
        year: 1999,
        title: 'Moral disengagement in the perpetration of inhumanities',
        venue: 'Personality and Social Psychology Review, 3(3), 193-209',
        doi: '10.1207/s15327957pspr0303_3',
      },
      {
        id: 'mccauley-moskalenko-2008-reuse',
        authors: 'Clark McCauley and Sophia Moskalenko',
        year: 2008,
        title: 'Mechanisms of political radicalization: Pathways toward terrorism',
        venue: 'Terrorism and Political Violence, 20(3), 415-433',
        doi: '10.1080/09546550802073367',
        note: 'Cited here for group mechanisms that can sit beside the 2003 sketch.',
      },
    ],
  },
  {
    id: '04',
    number: '04',
    title: 'The room that teaches',
    thesis:
      'Isolation, social identity, and group polarization can teach a circle that cruelty is ordinary. A famous network story still needs its later critique.',
    minutes: 10,
    chapters: [
      {
        id: '04-isolation',
        title: 'Isolation as a teacher',
        paragraphs: [
          'One of the 2008 group mechanisms is isolation. A circle that talks mainly to itself can shift what counts as a normal sentence. Jokes get harder. Targets get flatter. Dissent starts to sound like betrayal.',
          'Isolation does not require a locked room. A public thread can isolate if the replies that survive are only the ones that reward extremity. The mechanism is social, not architectural.',
          'This is still a mechanism, not a rate. Many isolated groups stay dull. The claim is that isolation is one way a room can teach, not that every small forum becomes violent.',
        ],
        visual: 'isolation-room',
      },
      {
        id: '04-identity',
        title: 'Us, them, and a thinner stranger',
        paragraphs: [
          'Tajfel and Turner’s social identity theory describes how people draw a we and a they, then favour the we. The original intergroup experiments were about trivial labels, not terrorism. The later theoretical claim is broader: once a category matters, people protect it, and they can derogate the out-group without a personal quarrel.',
          'In a political room, that can look like collective blame. A stranger is no longer a person with a day. They are a type. Combined with Borum’s later stages, a type is easier to place outside moral concern.',
          'Tajfel and Turner (1979) is a book chapter, “An integrative theory of intergroup conflict.” There is no DOI to open. The citation in Sources is the stable bibliographic record.',
        ],
      },
      {
        id: '04-polarisation',
        title: 'Like-minded rooms move the middle',
        paragraphs: [
          'Sunstein’s work on group polarization describes a regular finding: people who discuss a question with others who already lean the same way often leave more extreme than they arrived. The middle of the room moves. The tails get applause.',
          'Polarization is not the same as isolation, but they feed each other. A room that has already filtered dissent polarizes faster. A polarized room then treats remaining dissent as proof that outsiders cannot be reasoned with.',
          'Sunstein (2002), “The law of group polarization,” is in the Journal of Political Philosophy. The DOI is 10.1111/1467-9760.00148. It is a legal-theoretic restatement of a social-psychology result, not a study of any one platform.',
        ],
      },
      {
        id: '04-sageman',
        title: 'A network story, and the critique that followed',
        paragraphs: [
          'Marc Sageman’s Understanding Terror Networks (2004) argued that many jihadist plots of that period looked more like dense friendship clusters than like top-down cells. The “bunch of guys” phrase travelled farther than the book’s caveats.',
          'Bruce Hoffman (2008) answered that the network picture underplayed hierarchical organizations and leadership. Later case work has been less interested in picking a winner. Some plots look like Sageman’s clusters. Some look like Hoffman’s organizations. Some look like both at different times.',
          'Keep Sageman as one account of how a room can recruit through friendship. Keep the critique so the account does not become the only door. A network is a structure. It is not a verdict on a poster.',
        ],
      },
    ],
    sources: [
      {
        id: 'mccauley-moskalenko-2008-isolation',
        authors: 'Clark McCauley and Sophia Moskalenko',
        year: 2008,
        title: 'Mechanisms of political radicalization: Pathways toward terrorism',
        venue: 'Terrorism and Political Violence, 20(3), 415-433',
        doi: '10.1080/09546550802073367',
        note: 'Group isolation and like-minded extremity shift are the mechanisms this module leans on.',
      },
      {
        id: 'tajfel-turner-1979',
        authors: 'Henri Tajfel and John C. Turner',
        year: 1979,
        title: 'An integrative theory of intergroup conflict',
        venue:
          'In W. G. Austin and S. Worchel (Eds.), The social psychology of intergroup relations (pp. 33-47). Brooks/Cole',
        note: 'Book chapter. No DOI. Cited from the bibliographic record, not from a scan.',
      },
      {
        id: 'sunstein-2002',
        authors: 'Cass R. Sunstein',
        year: 2002,
        title: 'The law of group polarization',
        venue: 'Journal of Political Philosophy, 10(2), 175-195',
        doi: '10.1111/1467-9760.00148',
      },
      {
        id: 'sageman-2004',
        authors: 'Marc Sageman',
        year: 2004,
        title: 'Understanding terror networks',
        venue: 'University of Pennsylvania Press',
        note: 'Book. Read with the later Hoffman critique, not as a closed account.',
      },
      {
        id: 'hoffman-2008',
        authors: 'Bruce Hoffman',
        year: 2008,
        title: 'The myth of grass-roots terrorism',
        venue: 'Foreign Affairs, 87(3), 133-138',
        href: 'https://www.foreignaffairs.com/reviews/review-essay/2008-05-01/myth-grass-roots-terrorism',
        note: 'A direct critique of Sageman’s network-first picture.',
      },
    ],
  },
  {
    id: '05',
    number: '05',
    title: 'What the internet changes',
    thesis:
      'The internet changes speed, reach, and the mix of online and offline ties. It is a tool in studied cases, not a cause that replaces the older mechanisms.',
    minutes: 11,
    chapters: [
      {
        id: '05-conway',
        title: 'Ask a harder question',
        paragraphs: [
          'Maura Conway (2017) argued that research on the internet and violent extremism had spent too long on the existence question (does the internet matter?) and not enough on how, for whom, and compared with what. She offered six suggestions: better data, better comparison, less anecdote dressed as prevalence, and more attention to what is actually new.',
          'What is new is not grievance. Grievance is old. What can be new is scale, speed, the collapse of distance, and the way a stranger can join a room without entering a hall.',
          'The paper is in Studies in Conflict and Terrorism. The DOI is 10.1080/1057610X.2016.1157408. Treat it as a research agenda, not as a coefficient.',
        ],
      },
      {
        id: '05-mixed',
        title: 'Most studied paths are mixed',
        paragraphs: [
          'Herath and Whittaker (2023) coded online and offline ties for 231 Islamic State attackers and found few people who lived at either extreme. Their clusters include integrated paths (strong on both sides), encouraged paths (heavier online), enclosed paths (heavier offline, still using the internet to plan), and a smaller isolated set.',
          'The result is a spectrum, not a dichotomy. “Online radicalization” as a clean category does not survive that coding. People still meet, still phone, still sit in rooms. They also still download, still watch, still post.',
          'The paper is in Terrorism and Political Violence. The DOI is 10.1080/09546553.2021.1998008. The sample is Islamic State attackers, not a comment feed, and not this product’s collection.',
        ],
      },
      {
        id: '05-suler',
        title: 'Disinhibition is a setting, not a destiny',
        paragraphs: [
          'Suler (2004) described an online disinhibition effect: people say things in text, under a handle, that they would not say face to face. He split benign and toxic forms, and he listed contributing factors such as anonymity, invisibility, asynchronicity, and minimized authority.',
          'Disinhibition can make a slur cheaper to type. It does not decide that someone will type it, and it does not move them from a sentence to an act. It is a description of a setting that lowers a social cost.',
          'The paper is in CyberPsychology and Behavior. The DOI is 10.1089/1094931041291295. It is older than the platforms in later modules. The setting it names is still recognizable.',
        ],
      },
      {
        id: '05-tool',
        title: 'A tool, not a substitute for a cause',
        paragraphs: [
          'Gill and colleagues have spent a decade counting how terrorists use the internet: to learn, to communicate, to leak intent, to seek belonging. In that work, the internet is a tool that changes opportunity. It does not replace ideology, networks, or grievance, and it does not appear as a sufficient cause.',
          'Gill, Corner, Conway, Thornton, Bloom, and Horgan (2017) quantify those uses rather than arguing a single pathway. Combined with Conway’s agenda and Herath and Whittaker’s mixed clusters, the careful sentence is: the internet changes how older mechanisms run. It does not retire them.',
          'That is the limit this syllabus will keep when the next module talks about recommendation and imageboards.',
        ],
      },
    ],
    sources: [
      {
        id: 'conway-2017',
        authors: 'Maura Conway',
        year: 2017,
        title:
          'Determining the role of the internet in violent extremism and terrorism: Six suggestions for progressing research',
        venue: 'Studies in Conflict and Terrorism, 40(1), 77-98',
        doi: '10.1080/1057610X.2016.1157408',
      },
      {
        id: 'herath-whittaker-2023',
        authors: 'Chamin Herath and Joe Whittaker',
        year: 2023,
        title: 'Online radicalisation: Moving beyond a simple dichotomy',
        venue: 'Terrorism and Political Violence, 35(5), 1027-1048',
        doi: '10.1080/09546553.2021.1998008',
      },
      {
        id: 'suler-2004',
        authors: 'John Suler',
        year: 2004,
        title: 'The online disinhibition effect',
        venue: 'CyberPsychology and Behavior, 7(3), 321-326',
        doi: '10.1089/1094931041291295',
      },
      {
        id: 'gill-et-al-2017',
        authors: 'Paul Gill, Emily Corner, Maura Conway, Amy Thornton, Mia Bloom, and John Horgan',
        year: 2017,
        title:
          'Terrorist use of the internet by the numbers: Quantifying behaviors, patterns, and processes',
        venue: 'Criminology and Public Policy, 16(1), 99-117',
        doi: '10.1111/1745-9133.12249',
        note: 'Counts uses of the internet as a tool. It does not treat the internet as a cause that replaces older mechanisms.',
      },
    ],
  },
  {
    id: '06',
    number: '06',
    title: 'How rooms narrow',
    thesis:
      'Whether recommendation “pipelines” move ordinary viewers into extreme rooms is contested. Imageboards such as 4chan and 8chan appear in that literature as destinations. This page does not link to them.',
    minutes: 11,
    chapters: [
      {
        id: '06-contested',
        title: 'A pipeline that did not stay settled',
        paragraphs: [
          'A popular story says recommendation systems walk ordinary viewers from mainstream clips into narrower, more extreme rooms. Some audits found pathways that look like that. Later panel studies and a systematic review found a more mixed, and often weaker, picture.',
          'The honest teaching point is the contest, not a winner. Methods differ. Windows differ. Platforms change their rankers. A 2018 bot study and a 2020 panel study are not measuring the same object.',
          'This module stays with published audits and reviews. It does not import a pipeline coefficient into any other sample.',
        ],
      },
      {
        id: '06-ribeiro',
        title: 'What the FAT-star audit showed',
        paragraphs: [
          'Ribeiro, Ottoni, West, Almeida, and Meira (2020) audited YouTube recommendation traces and described radicalization pathways from milder political channels toward more extreme ones. The paper is in the FAT* 2020 proceedings. The DOI is 10.1145/3351095.3372879.',
          'An audit of recommendations is a study of what a ranker offered a crawler or a seeded account, in a window. It is not a study of what a representative person watched, and it is not a study of who later committed an act.',
          'The paper matters because it gave the pipeline story a careful method. It does not close the question.',
        ],
      },
      {
        id: '06-later',
        title: 'What later studies complicated',
        paragraphs: [
          'Chen, Nyhan, Reifler, Robertson, and Wilson (2023) paired survey attitudes with YouTube behaviour. They found that videos from alternative and extremist channels were watched mostly by a small set of people who already scored high on racial and gender resentment, who often subscribed to those channels, and who often arrived via external links. Recommendations from mainstream videos to those channels were rare in their 2020 window. The DOI is 10.1126/sciadv.add8080.',
          'Hosseinmardi and colleagues, in related YouTube work (including a 2021 PNAS consumption study and a later counterfactual-bot paper), likewise find that heavy consumption of extreme content is concentrated, and that following the recommender is not, on average, a walk into more extreme material after platform changes around 2019.',
          'Yesilada and Lewandowsky (2022) reviewed 23 YouTube-recommendation studies in Internet Policy Review. Fourteen implicated the recommender in pathways to problematic content, seven were mixed, and two were not. They also warn that researcher models may not match the live ranker. The pipeline is contested on purpose. The review is the place that says so in one table.',
        ],
      },
      {
        id: '06-imageboards',
        title: 'Naming narrower rooms without sending anyone there',
        paragraphs: [
          'Reporting and research on extreme online cultures often name imageboards such as 4chan and 8chan as destinations: smaller rooms with weaker moderation and a local reward for cruelty. This page names them so the path is not euphemized. It does not link to them.',
          'A destination in a case study is not a recommendation. It is also not proof that a large platform’s ranker delivered the person there. Arrival via search, a shared screenshot, a friend, or an off-platform link are all common in the later panel work.',
          'The teaching limit is the same as module 01. A narrower room can coincide with later harm. Naming the room is not a claim that the room produced the harm, and it is not an invitation to visit.',
        ],
      },
    ],
    sources: [
      {
        id: 'ribeiro-2020',
        authors:
          'Manoel Horta Ribeiro, Raphael Ottoni, Robert West, Virgílio A. F. Almeida, and Wagner Meira Jr.',
        year: 2020,
        title: 'Auditing radicalization pathways on YouTube',
        venue: 'Proceedings of FAT* 2020, 131-141',
        doi: '10.1145/3351095.3372879',
      },
      {
        id: 'chen-nyhan-2023',
        authors:
          'Annie Y. Chen, Brendan Nyhan, Jason Reifler, Ronald E. Robertson, and Christo Wilson',
        year: 2023,
        title:
          'Subscriptions and external links help drive resentful users to alternative and extremist YouTube channels',
        venue: 'Science Advances, 9(35), eadd8080',
        doi: '10.1126/sciadv.add8080',
        note: 'Often grouped with the Hosseinmardi YouTube programme. The DOI the syllabus named is this paper, whose authors are Chen and colleagues.',
      },
      {
        id: 'hosseinmardi-2021',
        authors:
          'Homa Hosseinmardi, Amir Ghasemian, Aaron Clauset, Markus Mobius, Duncan M. Rothschild, and Duncan J. Watts',
        year: 2021,
        title: 'Examining the consumption of radical content on YouTube',
        venue: 'Proceedings of the National Academy of Sciences, 118(32), e2101967118',
        doi: '10.1073/pnas.2101967118',
      },
      {
        id: 'yesilada-lewandowsky-2022',
        authors: 'Muhsin Yesilada and Stephan Lewandowsky',
        year: 2022,
        title: 'Systematic review: YouTube recommendations and problematic content',
        venue: 'Internet Policy Review, 11(1)',
        doi: '10.14763/2022.1.1652',
        href: 'https://policyreview.info/articles/analysis/systematic-review-youtube-recommendations-and-problematic-content',
      },
    ],
  },
  {
    id: '07',
    number: '07',
    title: 'Speech beside the street',
    thesis:
      'Müller and Schwarz measured German anti-refugee Facebook activity beside local incidents. The method travels. The coefficients do not.',
    minutes: 9,
    chapters: [
      {
        id: '07-sample',
        title: 'A German Facebook study, named as one',
        paragraphs: [
          'Müller and Schwarz (2021) study anti-refugee hate crime in Germany and posts on the Facebook pages of the Alternative für Deutschland, mainly in the years around the 2015 refugee arrival. The paper is in the Journal of the European Economic Association. The DOI is 10.1093/jeea/jvaa045.',
          'The sample is German, anti-refugee, and Facebook-specific. It is not a YouTube comment sample, not a North American sample, and not a measure of anti-Muslim classification on any other corpus. Those limits have to stay attached to every sentence that follows.',
          'Teach the paper as a method lesson. Do not import its numbers into another place or year.',
        ],
      },
      {
        id: '07-method',
        title: 'What the method can show',
        paragraphs: [
          'The authors combine local incident records with local Facebook activity. They look at whether places and weeks with more anti-refugee posts also show more anti-refugee incidents, and they use outages and other shocks so that a simple national mood is less likely to explain both.',
          'That design can support a careful claim: in that country, on that network, in that window, online speech and offline incidents moved together after the authors tried to rule out some shared causes. The paper’s own language is about social media and hate crime, not about a comment causing an assault.',
          'A reader who only remembers “Facebook caused attacks” has not read the paper. A reader who remembers “the two series were associated in a specified German window” has.',
        ],
      },
      {
        id: '07-no-import',
        title: 'Coefficients do not travel',
        paragraphs: [
          'Even a well identified local elasticity is a number about that sample. Carry the method: pair a speech series with an incident series, show the window, show the coverage, and do not hide the gaps. Leave the coefficient where it was estimated.',
          'Importing a German Facebook elasticity into another platform’s comment rate would be a category error. The populations differ. The networks differ. The targets named in the posts differ. The police data differ.',
          'If a later observatory sits a scoped speech series beside a reviewed event list, it is borrowing the idea of a paired window. It is not inheriting Müller and Schwarz’s estimate.',
        ],
      },
      {
        id: '07-wording',
        title: 'The strongest verb is “coincides with”',
        paragraphs: [
          'When two series move together, the disciplined English is “temporally associated with” or “coincides with.” Those phrases name a shared window. They do not name a cause.',
          'Stronger verbs are tempting because they sound like a finding. They are also how a careful paper gets flattened into a slogan. This syllabus will not do that flattening, and it will not let a dashboard do it with these modules as cover.',
          'If a study itself claims identification, quote that claim as the authors’ claim, attached to their sample. Do not launder it into a general law about speech and the street.',
        ],
      },
    ],
    sources: [
      {
        id: 'muller-schwarz-2021',
        authors: 'Karsten Müller and Carlo Schwarz',
        year: 2021,
        title: 'Fanning the flames of hate: Social media and hate crime',
        venue: 'Journal of the European Economic Association, 19(4), 2131-2167',
        doi: '10.1093/jeea/jvaa045',
        note: 'German anti-refugee Facebook and local incidents. Method only. Do not import the coefficients.',
      },
    ],
  },
  {
    id: '08',
    number: '08',
    title: 'What a scoped record can say',
    thesis:
      'Islamophobia names a pattern of treatment. A scoped record can count inside a window. It cannot count what it did not collect.',
    minutes: 9,
    chapters: [
      {
        id: '08-naming',
        title: 'Naming a pattern, not a mood',
        paragraphs: [
          'Before a record can count anything, it needs a name for the pattern. Georgetown’s Bridge Initiative describes Islamophobia as an exaggerated fear, hatred, and hostility toward Islam and Muslims that is kept alive by stereotypes and can become exclusion from social and civic life.',
          'The Runnymede Trust’s 2017 report, updating a 1997 intervention, treats Islamophobia as anti-Muslim racism: a pattern of treatment, not a private feeling and not a single slur. Both sources are trying to make a public phenomenon discussable. Neither is a classifier running on a comment sample.',
          'A name is not a rate. It is the start of a rate. The next pages are about what has to travel with any number that uses that name.',
        ],
      },
      {
        id: '08-numerator',
        title: 'The numerator is a count of what was labelled',
        paragraphs: [
          'A numerator is the count of items that met a definition in a window: posts labelled a certain way, incidents recorded a certain way, cases that passed a review. It is never “how much hate exists.”',
          'Two numerators with the same word on the axis can still be different objects. A model label, a human review, a police record, and a survey item are four different counting rules. Mixing them without saying so is how a chart starts to lie.',
          'If the definition is “classified as likely anti-Muslim hostility by a published rule,” say that. Do not promote the count to a fact about the world beyond the rule.',
        ],
      },
      {
        id: '08-denominator',
        title: 'Denominator and coverage are the rest of the sentence',
        paragraphs: [
          'A rate without a denominator is a slogan. The denominator is the set the numerator was taken from: comments collected, videos in the sample, recorded incidents in the jurisdiction. Change the denominator and the same numerator is a different claim.',
          'Coverage is whether the collection actually ran. Days with no ingest are gaps. A gap is not a quiet day. Drawing a missing window as zero is how a chart invents peace, or invents a drop, that the collectors never saw.',
          'A scoped record that shows its numerator, its denominator, its window, its sources, and its gaps can be argued with. A naked percentage cannot.',
        ],
      },
      {
        id: '08-use',
        title: 'What the record is for',
        paragraphs: [
          'A scoped record is for comparison inside its own limits. It can show whether a labelled series moved in a collected window. It can sit beside a reviewed event list and say the two coincided. It cannot speak for a platform it did not sample, and it cannot turn a commenter into a type that needs a file.',
          'Bridge and Runnymede give the pattern a name so communities and researchers can talk about treatment, not about a mood. Measurement literacy keeps that talk from overclaiming. The two jobs are different, and both are required before a number is worth carrying into a policy room.',
          'That is the end of the syllabus. The Sources page lists the naming texts. Earlier modules listed the radicalization studies. None of them is a substitute for the limits on this page.',
        ],
      },
    ],
    sources: [
      {
        id: 'bridge-islamophobia',
        authors: 'Georgetown University Bridge Initiative',
        year: 2024,
        title: 'What is Islamophobia?',
        venue: 'Bridge Initiative, Georgetown University',
        href: 'https://bridge.georgetown.edu/about-islamophobia/',
        note: 'A working definition of Islamophobia as a pattern of hostility and exclusion, not a dashboard classification.',
      },
      {
        id: 'runnymede-2017',
        authors: 'Runnymede Trust',
        year: 2017,
        title: 'Islamophobia: Still a challenge for us all',
        venue: 'Runnymede Trust',
        href: 'https://www.runnymedetrust.org/publications/islamophobia-still-a-challenge-for-us-all',
        note: 'Updates the 1997 Runnymede intervention. Treats Islamophobia as anti-Muslim racism, a pattern of treatment.',
      },
    ],
  },
];
